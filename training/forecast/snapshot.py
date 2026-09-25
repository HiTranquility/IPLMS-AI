"""Materialize a versioned occupancy dataset from raw session exports."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from app.infra.datalake.occupancy_reader import OccupancyHistoryReader
from training.forecast.dataset import discover_lot_ids, regularize_history


SCHEMA_VERSION = 1


def _parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def source_manifests(data_lake: Path) -> list[dict[str, str]]:
    root = data_lake / "raw" / "parking_sessions"
    output: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.manifest.json")) if root.exists() else []:
        output.append(
            {
                "file": path.relative_to(data_lake).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return output


def write_snapshot(
    rows: Iterable[dict[str, Any]],
    *,
    output_dir: Path,
    source_manifests: list[dict[str, str]],
    as_of: datetime,
    history_days: int,
    slot_seconds: int = 30 * 60,
) -> tuple[Path, Path, dict[str, Any]]:
    """Write immutable JSONL + manifest, returning both paths and metadata."""

    normalized_rows = sorted(
        (dict(row) for row in rows),
        key=lambda row: (str(row["parking_lot_id"]), int(row["timestamp"])),
    )
    if not normalized_rows:
        raise ValueError("cannot materialize an empty occupancy snapshot")

    encoded_rows = [
        (
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for row in normalized_rows
    ]
    content = b"".join(encoded_rows)
    digest = hashlib.sha256(content).hexdigest()
    identity = {
        "data_sha256": digest,
        "as_of": as_of.astimezone(timezone.utc).isoformat(),
        "history_days": history_days,
        "slot_seconds": slot_seconds,
        "source_manifests": source_manifests,
    }
    identity_digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    snapshot_id = f"occupancy-v{SCHEMA_VERSION}-{identity_digest[:16]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    data_file = output_dir / f"{snapshot_id}.jsonl"
    manifest_file = output_dir / f"{snapshot_id}.manifest.json"

    observed_count = sum(not bool(row.get("is_missing")) for row in normalized_rows)
    missing_count = len(normalized_rows) - observed_count
    manifest: dict[str, Any] = {
        "dataset": "occupancy_slots",
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of.astimezone(timezone.utc).isoformat(),
        "history_days": history_days,
        "slot_seconds": slot_seconds,
        "data_file": data_file.name,
        "sha256": digest,
        "row_count": len(normalized_rows),
        "observed_count": observed_count,
        "missing_count": missing_count,
        "missing_rate": missing_count / len(normalized_rows),
        "parking_lot_ids": sorted(
            {str(row["parking_lot_id"]) for row in normalized_rows}
        ),
        "min_timestamp": min(int(row["timestamp"]) for row in normalized_rows),
        "max_timestamp": max(int(row["timestamp"]) for row in normalized_rows),
        "source_manifests": source_manifests,
        "target_semantics": "average occupancy in a half-open fixed-width slot",
        "missing_semantics": "unknown; never interpreted as zero occupancy",
        "capacity_semantics": (
            "active non-INACTIVE slot count at export; not effective-dated history"
        ),
    }

    write_immutable(data_file, content)
    if manifest_file.exists():
        stored_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if (
            stored_manifest.get("snapshot_id") != snapshot_id
            or stored_manifest.get("sha256") != digest
        ):
            raise FileExistsError(f"immutable snapshot conflict: {manifest_file}")
        return data_file, manifest_file, stored_manifest
    manifest_content = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    write_immutable(manifest_file, manifest_content)
    return data_file, manifest_file, manifest


def write_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"immutable snapshot conflict: {path}")
        return
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.part")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_snapshot(manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load and verify a snapshot without allowing paths outside its directory."""

    resolved_manifest = manifest_path.resolve()
    manifest = json.loads(resolved_manifest.read_text(encoding="utf-8"))
    raw_data_file = Path(str(manifest.get("data_file") or ""))
    if not raw_data_file.name or raw_data_file.is_absolute():
        raise ValueError("snapshot data_file must be a relative path")
    data_file = (resolved_manifest.parent / raw_data_file).resolve()
    try:
        data_file.relative_to(resolved_manifest.parent)
    except ValueError as exc:
        raise ValueError("snapshot data_file must stay beside the manifest") from exc
    content = data_file.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != str(manifest.get("sha256") or ""):
        raise ValueError("snapshot checksum mismatch")

    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(content.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid snapshot JSONL at line {line_number}") from exc
    if len(rows) != int(manifest.get("row_count", -1)):
        raise ValueError("snapshot row_count mismatch")
    return manifest, rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an immutable regularized occupancy snapshot from raw exports."
    )
    parser.add_argument("--data-lake", type=Path, default=Path("data/datalake"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/datalake/curated/occupancy")
    )
    parser.add_argument("--lot-id", action="append", dest="lot_ids")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument(
        "--as-of",
        type=_parse_instant,
        default=datetime.now(timezone.utc),
        help="UTC/offset ISO-8601 cutoff; fixes the reproducible history window",
    )
    args = parser.parse_args()
    if args.days <= 0:
        parser.error("--days must be positive")

    lot_ids = sorted(set(args.lot_ids or discover_lot_ids(args.data_lake)))
    if not lot_ids:
        parser.error("no raw parking lot data found; run export_parking_sessions first")

    reader = OccupancyHistoryReader(base_path=args.data_lake)
    observed: list[dict[str, Any]] = []
    for lot_id in lot_ids:
        observed.extend(
            reader.load_historical_occupancy(
                lot_id,
                days=args.days,
                now=args.as_of,
            )
        )
    if not observed:
        parser.error("raw sessions produced no occupancy labels in the selected window")

    regularized = regularize_history(observed)
    data_file, manifest_file, manifest = write_snapshot(
        regularized,
        output_dir=args.output,
        source_manifests=source_manifests(args.data_lake),
        as_of=args.as_of,
        history_days=args.days,
    )
    print(
        json.dumps(
            {
                "snapshot_id": manifest["snapshot_id"],
                "data_file": str(data_file.resolve()),
                "manifest_file": str(manifest_file.resolve()),
                "row_count": manifest["row_count"],
                "missing_rate": manifest["missing_rate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
