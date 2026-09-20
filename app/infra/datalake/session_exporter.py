"""Incremental PostgreSQL → data-lake export for parking sessions.

The export deliberately excludes user, vehicle, plate and media fields. Forecast
training needs occupancy intervals, not personal identifiers or image evidence.
Each successful run writes an immutable JSONL object plus a manifest/checksum,
then advances a local watermark atomically.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from app.config import get_config
from app.core.exceptions import DataLakeError


_SCHEMA_VERSION = 1
_DATASET = "parking_sessions"
_COLUMNS = (
    "session_id",
    "parking_lot_id",
    "slot_id",
    "status",
    "start_time",
    "end_time",
    "check_in_method",
    "check_out_method",
    "ai_confidence_in",
    "ai_confidence_out",
    "capacity_at_export",
    "updated_at",
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _utc(value).isoformat().replace("+00:00", "Z")


def _parse_instant(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return _utc(value)
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return _utc(datetime.fromisoformat(normalized))
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 instant: {value}") from exc


@dataclass(frozen=True)
class SessionExportResult:
    data_file: Path
    manifest_file: Path
    record_count: int
    sha256: str
    watermark: datetime


class ParkingSessionExporter:
    """Stream changed sessions to an immutable partition without loading all rows."""

    def __init__(
        self,
        *,
        db_url: str | None = None,
        root_path: str | Path | None = None,
        connection_factory: Callable[[], Any] | None = None,
        batch_size: int | None = None,
    ) -> None:
        config = get_config()
        self.db_url = db_url or config.llm.database_url
        self.root_path = Path(root_path or config.datalake.local_path)
        self.connection_factory = connection_factory
        self.batch_size = max(1, batch_size or config.datalake.export_batch_size)

    @property
    def checkpoint_path(self) -> Path:
        return self.root_path / "_state" / f"{_DATASET}.json"

    def read_watermark(self) -> datetime:
        if not self.checkpoint_path.exists():
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
        try:
            payload = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            return _parse_instant(payload["watermark"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DataLakeError("Watermark data lake không hợp lệ.") from exc

    def export(
        self,
        *,
        since: str | datetime | None = None,
        until: str | datetime | None = None,
    ) -> SessionExportResult:
        lower_bound = _parse_instant(since) if since is not None else self.read_watermark()
        upper_bound = _parse_instant(until) if until is not None else datetime.now(timezone.utc)
        if upper_bound <= lower_bound:
            raise ValueError("until must be greater than since")

        partition = self.root_path / "raw" / _DATASET / f"export_date={upper_bound:%Y-%m-%d}"
        run_id = f"{upper_bound:%Y%m%dT%H%M%S}_{uuid4().hex[:8]}"
        data_file = partition / f"{run_id}.jsonl"
        manifest_file = partition / f"{run_id}.manifest.json"
        temporary_file = partition / f".{run_id}.jsonl.part"
        partition.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        record_count = 0
        min_updated_at: str | None = None
        max_updated_at: str | None = None
        connection = None
        try:
            connection = self._connect()
            with connection.cursor() as cursor:
                cursor.execute(self._query(), (lower_bound, upper_bound))
                with temporary_file.open("wb") as output:
                    while rows := cursor.fetchmany(self.batch_size):
                        for row in rows:
                            record = self._record(row)
                            encoded = (
                                json.dumps(
                                    record,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                )
                                + "\n"
                            ).encode("utf-8")
                            output.write(encoded)
                            digest.update(encoded)
                            record_count += 1
                            updated_at = record["updated_at"]
                            min_updated_at = min(min_updated_at or updated_at, updated_at)
                            max_updated_at = max(max_updated_at or updated_at, updated_at)

            os.replace(temporary_file, data_file)
            checksum = digest.hexdigest()
            manifest = {
                "dataset": _DATASET,
                "schema_version": _SCHEMA_VERSION,
                "format": "jsonl",
                "data_file": data_file.relative_to(self.root_path).as_posix(),
                "sha256": checksum,
                "record_count": record_count,
                "exported_at": _iso(datetime.now(timezone.utc)),
                "window": {
                    "after_exclusive": _iso(lower_bound),
                    "until_inclusive": _iso(upper_bound),
                },
                "min_updated_at": min_updated_at,
                "max_updated_at": max_updated_at,
                "contains_pii": False,
            }
            self._atomic_json(manifest_file, manifest)
            self._atomic_json(
                self.checkpoint_path,
                {
                    "dataset": _DATASET,
                    "schema_version": _SCHEMA_VERSION,
                    "watermark": _iso(upper_bound),
                    "last_manifest": manifest_file.relative_to(self.root_path).as_posix(),
                },
            )
            return SessionExportResult(
                data_file=data_file,
                manifest_file=manifest_file,
                record_count=record_count,
                sha256=checksum,
                watermark=upper_bound,
            )
        except (ValueError, DataLakeError):
            data_file.unlink(missing_ok=True)
            manifest_file.unlink(missing_ok=True)
            raise
        except Exception as exc:
            data_file.unlink(missing_ok=True)
            manifest_file.unlink(missing_ok=True)
            raise DataLakeError("Không export được parking_sessions sang data lake.") from exc
        finally:
            temporary_file.unlink(missing_ok=True)
            if connection is not None:
                connection.close()

    def _connect(self) -> Any:
        if self.connection_factory is not None:
            return self.connection_factory()
        try:
            import psycopg2

            return psycopg2.connect(self.db_url, connect_timeout=10)
        except Exception as exc:
            raise DataLakeError("Không kết nối được PostgreSQL để export data lake.") from exc

    @staticmethod
    def _query() -> str:
        return """
            SELECT ps.id::text,
                   slot.parking_lot_id::text,
                   ps.slot_id::text,
                   ps.status::text,
                   ps.start_time,
                   ps.end_time,
                   ps.check_in_method,
                   ps.check_out_method,
                   ps.ai_confidence_in,
                   ps.ai_confidence_out,
                   (
                       SELECT COUNT(*)::integer
                       FROM parking.parking_slots capacity_slot
                       WHERE capacity_slot.parking_lot_id = slot.parking_lot_id
                         AND capacity_slot.deleted_at IS NULL
                   ) AS capacity_at_export,
                   ps.updated_at
            FROM booking.parking_sessions ps
            JOIN parking.parking_slots slot ON slot.id = ps.slot_id
            WHERE ps.deleted_at IS NULL
              AND ps.updated_at > %s
              AND ps.updated_at <= %s
            ORDER BY ps.updated_at ASC, ps.id ASC
        """

    @staticmethod
    def _record(row: Any) -> dict[str, Any]:
        values = dict(zip(_COLUMNS, row))
        for name in ("start_time", "end_time", "updated_at"):
            values[name] = _iso(values[name])
        for name in ("ai_confidence_in", "ai_confidence_out"):
            value = values[name]
            values[name] = float(value) if value is not None else None
        values["capacity_at_export"] = int(values["capacity_at_export"] or 0)
        return values

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.part")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
