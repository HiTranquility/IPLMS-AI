"""Readiness checks for the Vision golden set and Forecast data lake.

This command is intentionally read-only. It does not create labels, fill missing
occupancy slots, or promote a model. Its job is to make data gaps explicit before
someone starts an evaluation or training run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_child(base: Path, relative: str) -> Path | None:
    candidate = Path(relative)
    if candidate.is_absolute():
        return None
    resolved_base = base.resolve()
    resolved_candidate = (resolved_base / candidate).resolve()
    try:
        resolved_candidate.relative_to(resolved_base)
    except ValueError:
        return None
    return resolved_candidate


def _instant(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def inspect_vision(golden_dir: Path, *, min_samples: int = 200) -> dict[str, Any]:
    manifest_path = golden_dir / "manifest.json"
    result: dict[str, Any] = {
        "scope": "vision",
        "manifest": str(manifest_path.resolve()),
        "minimum_samples": min_samples,
        "sample_count": 0,
        "tag_counts": {},
        "sources": {},
        "errors": [],
        "warnings": [],
        "ready": False,
    }
    if not manifest_path.exists():
        result["errors"].append("missing manifest.json")
        return result

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(f"cannot read manifest.json: {exc}")
        return result

    items = manifest.get("items")
    if not isinstance(items, list):
        result["errors"].append("manifest.items must be a list")
        return result

    images_dir = _safe_child(
        golden_dir, str(manifest.get("images_dir") or "images")
    )
    if images_dir is None:
        result["errors"].append("images_dir must stay inside the golden directory")
        return result
    tags: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    hashes: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            result["errors"].append(f"items[{index}] must be an object")
            continue
        filename = str(item.get("file") or "").strip()
        plate = str(item.get("plate") or "").strip()
        expected_hash = str(item.get("sha256") or "").strip().lower()
        if not filename or not plate or not expected_hash:
            result["errors"].append(
                f"items[{index}] requires file, plate, and sha256"
            )
            continue
        if expected_hash in hashes:
            result["errors"].append(f"duplicate sha256 at items[{index}]")
        hashes.add(expected_hash)
        image_path = _safe_child(images_dir, filename)
        if image_path is None:
            result["errors"].append(
                f"image path must stay inside images_dir: {filename}"
            )
            continue
        if not image_path.is_file():
            result["errors"].append(f"missing image: {filename}")
        elif _sha256(image_path) != expected_hash:
            result["errors"].append(f"checksum mismatch: {filename}")
        for tag in item.get("tags") or []:
            tags[str(tag)] += 1
        sources[str(item.get("source") or "unknown")] += 1

    result["sample_count"] = len(items)
    result["tag_counts"] = dict(sorted(tags.items()))
    result["sources"] = dict(sorted(sources.items()))
    if len(items) < min_samples:
        result["warnings"].append(
            f"golden set has {len(items)} samples; minimum gate is {min_samples}"
        )
    if items and not tags:
        result["warnings"].append(
            "no condition tags found (for example night, blur, glare, oblique)"
        )
    result["ready"] = not result["errors"] and len(items) >= min_samples
    return result


def inspect_forecast(
    data_lake: Path, *, min_history_days: int = 30
) -> dict[str, Any]:
    raw_root = data_lake / "raw" / "parking_sessions"
    state_path = data_lake / "_state" / "parking_sessions.json"
    result: dict[str, Any] = {
        "scope": "forecast",
        "data_lake": str(data_lake.resolve()),
        "minimum_history_days": min_history_days,
        "data_files": 0,
        "manifest_files": 0,
        "record_count": 0,
        "lot_history": {},
        "eligible_lots": [],
        "watermark_present": False,
        "synthetic_silver_files": [],
        "errors": [],
        "warnings": [],
        "ready": False,
    }

    silver_root = data_lake / "silver" / "parking_sessions"
    if silver_root.exists():
        result["synthetic_silver_files"] = [
            str(path.relative_to(data_lake))
            for path in sorted(silver_root.glob("*historical*"))
            if path.is_file()
        ]

    jsonl_files = sorted(raw_root.rglob("*.jsonl")) if raw_root.exists() else []
    manifests = sorted(raw_root.rglob("*.manifest.json")) if raw_root.exists() else []
    result["data_files"] = len(jsonl_files)
    result["manifest_files"] = len(manifests)

    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if _instant(state.get("watermark")) is None:
                result["errors"].append("incremental export watermark is invalid")
            else:
                result["watermark_present"] = True
        except (OSError, AttributeError, json.JSONDecodeError) as exc:
            result["errors"].append(f"cannot read incremental export watermark: {exc}")

    covered_data_files: set[Path] = set()
    for manifest_path in manifests:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            relative_name = str(manifest["data_file"])
            data_file = _safe_child(data_lake, relative_name)
            if data_file is None:
                result["errors"].append(
                    f"manifest data_file escapes data lake: {relative_name}"
                )
                continue
            relative_data_file = data_file.relative_to(data_lake.resolve())
            if not data_file.is_file():
                result["errors"].append(
                    f"manifest points to missing data file: {relative_data_file.as_posix()}"
                )
                continue
            covered_data_files.add(data_file.resolve())
            actual_hash = _sha256(data_file)
            if actual_hash != str(manifest.get("sha256") or ""):
                result["errors"].append(
                    f"checksum mismatch: {relative_data_file.as_posix()}"
                )
            with data_file.open(encoding="utf-8") as handle:
                actual_count = sum(1 for line in handle if line.strip())
            if actual_count != int(manifest.get("record_count", -1)):
                result["errors"].append(
                    f"record_count mismatch: {relative_data_file.as_posix()}"
                )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            result["errors"].append(
                f"invalid manifest {manifest_path.name}: {exc}"
            )

    for data_file in jsonl_files:
        if data_file.resolve() not in covered_data_files:
            result["errors"].append(
                f"data file has no valid manifest: {data_file.relative_to(data_lake).as_posix()}"
            )

    lot_times: dict[str, list[datetime]] = defaultdict(list)
    lot_records: Counter[str] = Counter()
    for data_file in jsonl_files:
        try:
            with data_file.open(encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    result["record_count"] += 1
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        result["errors"].append(
                            f"invalid JSON: {data_file.name}:{line_number}"
                        )
                        continue
                    lot_id = str(row.get("parking_lot_id") or "").strip()
                    start = _instant(row.get("start_time"))
                    if not lot_id or start is None:
                        result["errors"].append(
                            f"missing parking_lot_id/start_time: {data_file.name}:{line_number}"
                        )
                        continue
                    capacity = int(row.get("capacity_at_export") or 0)
                    if capacity <= 0:
                        result["errors"].append(
                            f"non-positive capacity: {data_file.name}:{line_number}"
                        )
                    lot_records[lot_id] += 1
                    lot_times[lot_id].append(start)
                    end = _instant(row.get("end_time"))
                    if end is not None:
                        lot_times[lot_id].append(end)
        except OSError as exc:
            result["errors"].append(f"cannot read {data_file.name}: {exc}")

    for lot_id in sorted(lot_times):
        first = min(lot_times[lot_id])
        last = max(lot_times[lot_id])
        history_days = max(0.0, (last - first).total_seconds() / 86400)
        result["lot_history"][lot_id] = {
            "records": lot_records[lot_id],
            "first_event": first.isoformat(),
            "last_event": last.isoformat(),
            "history_days": round(history_days, 2),
        }
        if history_days >= min_history_days:
            result["eligible_lots"].append(lot_id)

    if not jsonl_files:
        result["warnings"].append("no raw PostgreSQL export found")
    if not state_path.is_file():
        result["warnings"].append("incremental export watermark is missing")
    if result["synthetic_silver_files"]:
        result["warnings"].append(
            "synthetic silver data exists but is not accepted as production training evidence"
        )
    if lot_times and not result["eligible_lots"]:
        result["warnings"].append(
            f"no parking lot has at least {min_history_days} days of history"
        )

    result["ready"] = (
        bool(result["eligible_lots"])
        and result["watermark_present"]
        and not result["errors"]
    )
    return result


def _print_scope(report: dict[str, Any]) -> None:
    status = "READY" if report["ready"] else "NOT READY"
    print(f"[{status}] {report['scope'].upper()}")
    if report["scope"] == "vision":
        print(
            f"  samples: {report['sample_count']}/{report['minimum_samples']}  "
            f"tags: {report['tag_counts']}"
        )
    else:
        print(
            f"  raw files: {report['data_files']}  records: {report['record_count']}  "
            f"eligible lots: {len(report['eligible_lots'])}"
        )
    for message in report["errors"]:
        print(f"  ERROR: {message}")
    for message in report["warnings"]:
        print(f"  WARN : {message}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only readiness gates for Vision evaluation and Forecast training."
    )
    parser.add_argument("--scope", choices=("all", "vision", "forecast"), default="all")
    parser.add_argument("--golden-dir", type=Path, default=Path("data/golden/plates"))
    parser.add_argument("--data-lake", type=Path, default=Path("data/datalake"))
    parser.add_argument("--min-vision-samples", type=int, default=200)
    parser.add_argument("--min-forecast-days", type=int, default=30)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    reports: list[dict[str, Any]] = []
    if args.scope in ("all", "vision"):
        reports.append(
            inspect_vision(args.golden_dir, min_samples=args.min_vision_samples)
        )
    if args.scope in ("all", "forecast"):
        reports.append(
            inspect_forecast(args.data_lake, min_history_days=args.min_forecast_days)
        )

    payload = {"ready": all(report["ready"] for report in reports), "reports": reports}
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for index, report in enumerate(reports):
            if index:
                print()
            _print_scope(report)
    return 0 if payload["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
