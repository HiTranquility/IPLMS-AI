"""Read exported sessions and build leakage-safe 30-minute occupancy labels."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.config import get_config
from app.core.exceptions import DataLakeError


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class OccupancyHistoryReader:
    def __init__(self, base_path: str | Path | None = None, slot_minutes: int | None = None):
        config = get_config().datalake
        self.base_path = Path(base_path or config.local_path)
        self.slot_minutes = max(1, slot_minutes or config.occupancy_slot_minutes)

    def load_historical_occupancy(
        self,
        parking_lot_id: str,
        days: int = 30,
        *,
        now: datetime | None = None,
    ) -> List[Dict[str, Any]]:
        if not parking_lot_id.strip():
            raise ValueError("parking_lot_id is required")
        if days <= 0:
            raise ValueError("days must be positive")

        end = now or datetime.now(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        else:
            end = end.astimezone(timezone.utc)
        start = end - timedelta(days=days)
        sessions = self._latest_sessions(self._records())
        slot_seconds = self.slot_minutes * 60
        aggregates: dict[int, dict[str, float | int]] = {}

        for record in sessions.values():
            if record.get("parking_lot_id") != parking_lot_id or not record.get("start_time"):
                continue
            session_start = max(start, _instant(record["start_time"]))
            raw_end = record.get("end_time")
            session_end = min(end, _instant(raw_end) if raw_end else end)
            if session_end <= session_start:
                continue

            capacity = int(record.get("capacity_at_export") or 0)
            if capacity <= 0:
                continue
            cursor = int(session_start.timestamp()) // slot_seconds * slot_seconds
            while cursor < int(session_end.timestamp()):
                slot_start = datetime.fromtimestamp(cursor, timezone.utc)
                slot_end = slot_start + timedelta(seconds=slot_seconds)
                overlap = max(
                    0.0,
                    (min(session_end, slot_end) - max(session_start, slot_start)).total_seconds(),
                )
                if overlap:
                    bucket = aggregates.setdefault(
                        cursor,
                        {"occupied_seconds": 0.0, "capacity": capacity, "session_count": 0},
                    )
                    bucket["occupied_seconds"] = float(bucket["occupied_seconds"]) + overlap
                    bucket["capacity"] = max(int(bucket["capacity"]), capacity)
                    bucket["session_count"] = int(bucket["session_count"]) + 1
                cursor += slot_seconds

        output: List[Dict[str, Any]] = []
        for timestamp, aggregate in sorted(aggregates.items()):
            slot_start = datetime.fromtimestamp(timestamp, timezone.utc)
            capacity = int(aggregate["capacity"])
            occupied_equivalent = float(aggregate["occupied_seconds"]) / slot_seconds
            occupancy = min(1.0, occupied_equivalent / capacity)
            output.append(
                {
                    "timestamp": timestamp,
                    "datetime_iso": slot_start.isoformat().replace("+00:00", "Z"),
                    "parking_lot_id": parking_lot_id,
                    "capacity": capacity,
                    "occupied_equivalent": round(occupied_equivalent, 4),
                    "avg_occupancy": round(occupancy, 6),
                    "occupancy_percent": round(occupancy * 100, 4),
                    "session_count": int(aggregate["session_count"]),
                    "day_of_week": slot_start.weekday(),
                    "hour": slot_start.hour,
                    # No row is manufactured for an empty interval: absence can
                    # mean zero occupancy or missing exports, so callers must
                    # keep this quality boundary explicit.
                    "data_quality": "observed_sessions_only",
                }
            )
        return output

    def _records(self) -> Iterable[dict[str, Any]]:
        raw_root = self.base_path / "raw" / "parking_sessions"
        if not raw_root.exists():
            return
        try:
            for path in sorted(raw_root.rglob("*.jsonl")):
                with path.open("r", encoding="utf-8") as source:
                    for line_number, line in enumerate(source, start=1):
                        if not line.strip():
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise DataLakeError(
                                f"JSONL data lake lỗi tại {path.name}:{line_number}."
                            ) from exc
        except OSError as exc:
            raise DataLakeError("Không đọc được parking_sessions từ data lake.") from exc

    @staticmethod
    def _latest_sessions(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for record in records:
            session_id = str(record.get("session_id") or "")
            updated_at = record.get("updated_at")
            if not session_id or not updated_at:
                continue
            previous = latest.get(session_id)
            if previous is None or _instant(updated_at) > _instant(previous["updated_at"]):
                latest[session_id] = record
        return latest


occupancy_reader = OccupancyHistoryReader()
