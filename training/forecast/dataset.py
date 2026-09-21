"""Dataset preparation for occupancy forecasting.

The important contract in this module is that a missing time slot remains missing.
It must never be converted to zero occupancy, because that would create a false
training label and bias the model towards predicting an empty parking lot.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable


def _timestamp(row: dict[str, Any]) -> int:
    value = row.get("timestamp")
    if value is None:
        raise ValueError("history row is missing timestamp")
    return int(value)


def _target(row: dict[str, Any]) -> float:
    if row.get("avg_occupancy") is not None:
        value = float(row["avg_occupancy"])
    elif row.get("occupancy_percent") is not None:
        value = float(row["occupancy_percent"]) / 100.0
    else:
        raise ValueError("history row is missing avg_occupancy")

    if not 0.0 <= value <= 1.0:
        raise ValueError(f"occupancy target must be between 0 and 1, got {value}")
    return value


def _iso_utc(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def regularize_history(
    rows: Iterable[dict[str, Any]], *, slot_seconds: int = 30 * 60
) -> list[dict[str, Any]]:
    """Return a fixed-frequency series while preserving missing labels.

    Input rows are grouped by ``parking_lot_id``. Every absent slot between the
    first and last observed slot is emitted with ``target_occupancy=None`` and
    ``is_missing=True``. Duplicate timestamps are rejected so accidental data
    duplication cannot silently change a training target.
    """

    if slot_seconds <= 0:
        raise ValueError("slot_seconds must be positive")

    grouped: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for raw in rows:
        lot_id = str(raw.get("parking_lot_id") or "").strip()
        if not lot_id:
            raise ValueError("history row is missing parking_lot_id")
        timestamp = _timestamp(raw)
        if timestamp % slot_seconds:
            raise ValueError(
                f"timestamp {timestamp} is not aligned to {slot_seconds}-second slots"
            )
        if timestamp in grouped[lot_id]:
            raise ValueError(
                f"duplicate history slot for parking_lot_id={lot_id}, timestamp={timestamp}"
            )
        grouped[lot_id][timestamp] = dict(raw)

    result: list[dict[str, Any]] = []
    for lot_id in sorted(grouped):
        observed = grouped[lot_id]
        if not observed:
            continue
        first_timestamp = min(observed)
        last_timestamp = max(observed)
        for timestamp in range(first_timestamp, last_timestamp + slot_seconds, slot_seconds):
            raw = observed.get(timestamp)
            if raw is None:
                result.append(
                    {
                        "parking_lot_id": lot_id,
                        "timestamp": timestamp,
                        "datetime_iso": _iso_utc(timestamp),
                        "target_occupancy": None,
                        "is_missing": True,
                        "data_quality": "missing",
                        "capacity": None,
                    }
                )
                continue

            result.append(
                {
                    "parking_lot_id": lot_id,
                    "timestamp": timestamp,
                    "datetime_iso": raw.get("datetime_iso") or _iso_utc(timestamp),
                    "target_occupancy": _target(raw),
                    "is_missing": False,
                    "data_quality": raw.get("data_quality", "observed"),
                    "capacity": raw.get("capacity"),
                }
            )

    return result


def discover_lot_ids(data_lake: Path) -> list[str]:
    """Discover lot IDs only from production-contract raw session exports."""

    lot_ids: set[str] = set()
    raw_root = data_lake / "raw" / "parking_sessions"
    for path in raw_root.rglob("*.jsonl") if raw_root.exists() else []:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                lot_id = str(payload.get("parking_lot_id") or "").strip()
                if lot_id:
                    lot_ids.add(lot_id)
    return sorted(lot_ids)
