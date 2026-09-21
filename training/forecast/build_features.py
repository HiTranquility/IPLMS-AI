"""Build immutable point-in-time feature splits from an occupancy snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from training.forecast.features import build_feature_rows, temporal_split
from training.forecast.snapshot import load_snapshot, write_immutable


SCHEMA_VERSION = 1


def _positive_csv(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not parsed or any(item <= 0 for item in parsed):
        raise argparse.ArgumentTypeError("all values must be positive")
    return parsed


def _encode_rows(rows: Sequence[dict[str, Any]]) -> bytes:
    return b"".join(
        (
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for row in rows
    )


def write_feature_dataset(
    split: dict[str, list[dict[str, Any]]],
    *,
    output_dir: Path,
    source_snapshot: dict[str, Any],
    horizons: Sequence[int],
    lag_slots: Sequence[int],
    rolling_windows: Sequence[int],
    validation_fraction: float,
    test_fraction: float,
) -> tuple[Path, dict[str, Any]]:
    config = {
        "source_snapshot_id": source_snapshot["snapshot_id"],
        "horizons": list(horizons),
        "lag_slots": list(lag_slots),
        "rolling_windows": list(rolling_windows),
        "validation_fraction": validation_fraction,
        "test_fraction": test_fraction,
    }
    feature_columns = sorted(
        {
            key
            for rows in split.values()
            for row in rows
            for key in row
            if key
            not in {
                "parking_lot_id",
                "origin_timestamp",
                "target_timestamp",
                "horizon_slots",
                "target_occupancy",
                "last_observed_timestamp",
            }
        }
    )
    encoded_splits = {name: _encode_rows(rows) for name, rows in split.items()}
    split_hashes = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in encoded_splits.items()
    }
    identity = {"config": config, "split_hashes": split_hashes}
    identity_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    artifact_id = f"forecast-features-v{SCHEMA_VERSION}-{identity_hash[:16]}"
    artifact_dir = output_dir / artifact_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {}
    for name, content in encoded_splits.items():
        path = artifact_dir / f"{name}.jsonl"
        write_immutable(path, content)
        files[name] = path.name

    manifest_path = artifact_dir / "manifest.json"
    if manifest_path.exists():
        stored = json.loads(manifest_path.read_text(encoding="utf-8"))
        if stored.get("artifact_id") != artifact_id:
            raise FileExistsError(f"immutable feature artifact conflict: {manifest_path}")
        return manifest_path, stored

    manifest: dict[str, Any] = {
        "dataset": "forecast_features",
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **config,
        "files": files,
        "split_hashes": split_hashes,
        "split_counts": {name: len(rows) for name, rows in split.items()},
        "feature_columns": feature_columns,
        "leakage_guard": (
            "occupancy features use timestamps <= origin; targets crossing "
            "validation/test origin boundaries are purged"
        ),
    }
    write_immutable(
        manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    return manifest_path, manifest


def load_feature_dataset(
    manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Verify and load every immutable feature split."""

    resolved_manifest = manifest_path.resolve()
    manifest = json.loads(resolved_manifest.read_text(encoding="utf-8"))
    files = manifest.get("files") or {}
    expected_hashes = manifest.get("split_hashes") or {}
    expected_counts = manifest.get("split_counts") or {}
    splits: dict[str, list[dict[str, Any]]] = {}
    for name in ("train", "validation", "test", "purged"):
        raw_path = Path(str(files.get(name) or ""))
        if not raw_path.name or raw_path.is_absolute():
            raise ValueError(f"feature split path is invalid: {name}")
        path = (resolved_manifest.parent / raw_path).resolve()
        try:
            path.relative_to(resolved_manifest.parent)
        except ValueError as exc:
            raise ValueError(f"feature split escapes artifact directory: {name}") from exc
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != str(expected_hashes.get(name) or ""):
            raise ValueError(f"feature split checksum mismatch: {name}")
        rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
        if len(rows) != int(expected_counts.get(name, -1)):
            raise ValueError(f"feature split row count mismatch: {name}")
        splits[name] = rows
    return manifest, splits


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build train/validation/test feature artifacts from a snapshot."
    )
    parser.add_argument("--snapshot-manifest", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("data/datalake/curated/forecast_features")
    )
    parser.add_argument("--horizons", type=_positive_csv, default=(1, 2, 4, 8))
    parser.add_argument("--lags", type=_positive_csv, default=(1, 2, 48, 336))
    parser.add_argument("--rolling-windows", type=_positive_csv, default=(4, 48))
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    args = parser.parse_args()

    snapshot, rows = load_snapshot(args.snapshot_manifest)
    features = build_feature_rows(
        rows,
        horizons=args.horizons,
        lag_slots=args.lags,
        rolling_windows=args.rolling_windows,
    )
    if not features:
        parser.error("snapshot produced no supervised feature rows")
    try:
        split = temporal_split(
            features,
            validation_fraction=args.validation_fraction,
            test_fraction=args.test_fraction,
        )
    except ValueError as exc:
        parser.error(str(exc))

    manifest_path, manifest = write_feature_dataset(
        split,
        output_dir=args.output,
        source_snapshot=snapshot,
        horizons=args.horizons,
        lag_slots=args.lags,
        rolling_windows=args.rolling_windows,
        validation_fraction=args.validation_fraction,
        test_fraction=args.test_fraction,
    )
    print(
        json.dumps(
            {
                "artifact_id": manifest["artifact_id"],
                "manifest": str(manifest_path.resolve()),
                "split_counts": manifest["split_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
