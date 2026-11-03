import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from app.core.exceptions import DataLakeError
from app.infra.datalake import OccupancyReader, SessionExporter


UTC = timezone.utc


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.offset = 0
        self.params = None
        self.query = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchmany(self, size):
        batch = self.rows[self.offset : self.offset + size]
        self.offset += len(batch)
        return batch


class _Connection:
    def __init__(self, rows):
        self.cursor_instance = _Cursor(rows)
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


class SessionExporterTest(unittest.TestCase):
    def test_requires_an_explicit_operational_database(self):
        exporter = SessionExporter(db_url="")

        with self.assertRaisesRegex(
            DataLakeError, "AI_DATALAKE_SOURCE_DATABASE_URL"
        ):
            exporter._connect()

    def test_export_streams_non_pii_rows_and_advances_watermark(self):
        updated = datetime(2026, 9, 20, 1, 0, tzinfo=UTC)
        rows = [
            (
                "session-1",
                "lot-1",
                "slot-1",
                "completed",
                datetime(2026, 9, 20, 0, 0, tzinfo=UTC),
                datetime(2026, 9, 20, 0, 30, tzinfo=UTC),
                "AUTO_ALPR",
                "AUTO_ALPR",
                Decimal("92.50"),
                Decimal("90.00"),
                100,
                updated,
            )
        ]
        connection = _Connection(rows)
        with tempfile.TemporaryDirectory() as directory:
            exporter = SessionExporter(
                root_path=directory,
                connection_factory=lambda: connection,
                batch_size=1,
            )
            result = exporter.export(
                since="2026-09-19T00:00:00Z",
                until="2026-09-20T02:00:00Z",
            )

            content = result.data_file.read_bytes()
            record = json.loads(content.decode("utf-8"))
            manifest = json.loads(result.manifest_file.read_text(encoding="utf-8"))
            checkpoint = json.loads(exporter.checkpoint_path.read_text(encoding="utf-8"))

            self.assertEqual(result.record_count, 1)
            self.assertEqual(result.sha256, hashlib.sha256(content).hexdigest())
            self.assertEqual(record["parking_lot_id"], "lot-1")
            self.assertEqual(record["ai_confidence_in"], 92.5)
            self.assertNotIn("user_id", record)
            self.assertNotIn("vehicle_id", record)
            self.assertNotIn("image_url", record)
            self.assertFalse(manifest["contains_pii"])
            self.assertEqual(checkpoint["watermark"], "2026-09-20T02:00:00Z")
            self.assertIn(
                "capacity_slot.status <> 'INACTIVE'",
                connection.cursor_instance.query,
            )
            self.assertTrue(connection.closed)

    def test_export_does_not_leave_partition_when_checkpoint_fails(self):
        connection = _Connection([])
        with tempfile.TemporaryDirectory() as directory:
            exporter = SessionExporter(
                root_path=directory,
                connection_factory=lambda: connection,
            )
            real_atomic_json = exporter._atomic_json

            def fail_checkpoint(path, payload):
                if path == exporter.checkpoint_path:
                    raise OSError("disk full")
                real_atomic_json(path, payload)

            with patch.object(exporter, "_atomic_json", side_effect=fail_checkpoint):
                with self.assertRaises(DataLakeError):
                    exporter.export(
                        since="2026-09-19T00:00:00Z",
                        until="2026-09-20T02:00:00Z",
                    )

            partition = Path(directory) / "raw" / "parking_sessions"
            self.assertEqual(list(partition.rglob("*.jsonl")), [])
            self.assertEqual(list(partition.rglob("*.manifest.json")), [])
            self.assertFalse(exporter.checkpoint_path.exists())
            self.assertTrue(connection.closed)


class OccupancyReaderTest(unittest.TestCase):
    def test_deduplicates_incremental_rows_and_aggregates_half_open_slots(self):
        records = [
            {
                "session_id": "session-1",
                "parking_lot_id": "lot-1",
                "start_time": "2026-01-01T00:10:00Z",
                "end_time": "2026-01-01T00:40:00Z",
                "capacity_at_export": 2,
                "updated_at": "2026-01-01T01:00:00Z",
            },
            {
                "session_id": "session-1",
                "parking_lot_id": "lot-1",
                "start_time": "2026-01-01T00:10:00Z",
                "end_time": "2026-01-01T01:00:00Z",
                "capacity_at_export": 2,
                "updated_at": "2026-01-01T01:30:00Z",
            },
            {
                "session_id": "session-2",
                "parking_lot_id": "lot-1",
                "start_time": "2026-01-01T00:30:00Z",
                "end_time": "2026-01-01T00:45:00Z",
                "capacity_at_export": 2,
                "updated_at": "2026-01-01T01:10:00Z",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw" / "parking_sessions" / "export_date=2026-01-01"
            raw.mkdir(parents=True)
            (raw / "part.jsonl").write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )

            result = OccupancyReader(directory, slot_minutes=30).load_historical_occupancy(
                "lot-1",
                days=1,
                now=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
            )

            self.assertEqual(len(result), 2)
            self.assertAlmostEqual(result[0]["avg_occupancy"], 1 / 3, places=6)
            self.assertEqual(result[1]["avg_occupancy"], 0.75)
            self.assertEqual(result[1]["session_count"], 2)
            self.assertEqual(result[1]["data_quality"], "observed_sessions_only")

    def _write_sessions(self, directory, records, windows):
        raw = Path(directory) / "raw" / "parking_sessions" / "export_date=2026-01-01"
        raw.mkdir(parents=True)
        (raw / "part.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
        )
        for index, (after, until) in enumerate(windows):
            (raw / f"run{index}.manifest.json").write_text(
                json.dumps({"window": {"after_exclusive": after, "until_inclusive": until}}),
                encoding="utf-8",
            )

    def test_empty_slots_inside_contiguous_export_coverage_are_zero(self):
        records = [
            {
                "session_id": "s-1",
                "parking_lot_id": "lot-1",
                "start_time": "2026-01-01T00:00:00Z",
                "end_time": "2026-01-01T00:30:00Z",
                "capacity_at_export": 2,
                "updated_at": "2026-01-01T00:30:00Z",
            }
        ]
        windows = [
            ("1970-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
            ("2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            self._write_sessions(directory, records, windows)
            reader = OccupancyReader(directory, slot_minutes=30)
            self.assertEqual(reader.coverage_end(), datetime(2026, 1, 1, 2, 0, tzinfo=UTC))
            result = reader.load_historical_occupancy(
                "lot-1", days=1, now=datetime(2026, 1, 1, 3, 0, tzinfo=UTC)
            )

        self.assertEqual([row["avg_occupancy"] for row in result], [0.5, 0.0, 0.0, 0.0])
        self.assertEqual(result[0]["data_quality"], "observed_sessions_only")
        self.assertEqual(
            result[1]["data_quality"], "observed_zero_within_export_coverage"
        )
        # 02:00–03:00 nằm sau vùng phủ: vẫn là thiếu, không phải 0%.
        self.assertEqual(result[-1]["datetime_iso"], "2026-01-01T01:30:00Z")

    def test_export_gap_stops_zero_filling(self):
        records = [
            {
                "session_id": "s-1",
                "parking_lot_id": "lot-1",
                "start_time": "2026-01-01T00:00:00Z",
                "end_time": "2026-01-01T00:30:00Z",
                "capacity_at_export": 2,
                "updated_at": "2026-01-01T00:30:00Z",
            }
        ]
        windows = [
            ("1970-01-01T00:00:00Z", "2026-01-01T00:30:00Z"),
            # Export lẻ bằng `since`: lỗ hổng 00:30–01:30 không được tính là trống.
            ("2026-01-01T01:30:00Z", "2026-01-01T03:00:00Z"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            self._write_sessions(directory, records, windows)
            reader = OccupancyReader(directory, slot_minutes=30)
            self.assertEqual(
                reader.coverage_end(), datetime(2026, 1, 1, 0, 30, tzinfo=UTC)
            )
            result = reader.load_historical_occupancy(
                "lot-1", days=1, now=datetime(2026, 1, 1, 3, 0, tzinfo=UTC)
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["data_quality"], "observed_sessions_only")


if __name__ == "__main__":
    unittest.main()
