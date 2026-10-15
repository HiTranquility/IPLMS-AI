"""Unit tests cho ParquetLakeReader - nạp dữ liệu Parquet Data Lake cho huấn luyện AI Forecast."""
from __future__ import annotations

from datetime import datetime, timezone
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

# Ensure 'ai' root is on sys.path for direct python -m unittest runs
_AI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

import pyarrow as pa
import pyarrow.parquet as pq

from app.core.exceptions import DataLakeError
from app.core.forecast.readers import ParquetLakeReader, parquet_lake_reader
from app.core.forecast.services.forecast_service import ForecastService


class ParquetLakeReaderTest(unittest.TestCase):
    """Bộ kiểm thử toàn diện cho ParquetLakeReader."""

    def setUp(self):
        self.reader = ParquetLakeReader()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_and_read_occupancy_parquet_file(self):
        """Kiểm tra ghi và đọc lại file Parquet mẫu trên ổ đĩa."""
        sample_records = [
            {
                "area_id": "lot-downtown-01",
                "timestamp": 1700000000,
                "occupied_slots": 42,
                "total_slots": 100,
                "occupancy_ratio": 0.42,
            },
            {
                "area_id": "lot-downtown-01",
                "timestamp": 1700003600,
                "occupied_slots": 85,
                "total_slots": 100,
                "occupancy_ratio": 0.85,
            },
        ]
        file_path = self.test_dir / "test_occupancy.parquet"

        # 1. Ghi file Parquet
        written_count = self.reader.write_occupancy_parquet(sample_records, file_path)
        self.assertEqual(written_count, 2)
        self.assertTrue(file_path.exists())

        # 2. Đọc lại file Parquet
        records = self.reader.read_occupancy_parquet(file_path)
        self.assertEqual(len(records), 2)

        # 3. Kiểm tra các trường dữ liệu chuẩn hóa
        r1 = records[0]
        self.assertEqual(r1["area_id"], "lot-downtown-01")
        self.assertEqual(r1["timestamp"], 1700000000)
        self.assertEqual(r1["occupied_slots"], 42)
        self.assertEqual(r1["total_slots"], 100)
        self.assertAlmostEqual(r1["occupancy_ratio"], 0.42, places=4)
        self.assertFalse(r1["is_fallback"])
        self.assertIn("day_of_week", r1)
        self.assertIn("hour_of_day", r1)
        self.assertIn("datetime_iso", r1)

        r2 = records[1]
        self.assertEqual(r2["area_id"], "lot-downtown-01")
        self.assertEqual(r2["timestamp"], 1700003600)
        self.assertEqual(r2["occupied_slots"], 85)
        self.assertAlmostEqual(r2["occupancy_ratio"], 0.85, places=4)

    def test_write_and_read_parquet_buffer(self):
        """Kiểm tra đọc và ghi Parquet trực tiếp từ bộ nhớ BytesIO/bytes (MinIO/S3 buffer)."""
        sample_records = [
            {
                "area_id": "lot-buffer-01",
                "timestamp": 1700000000,
                "occupied_slots": 30,
                "total_slots": 60,
                "occupancy_ratio": 0.50,
            }
        ]

        # Ghi vào in-memory buffer
        buffer = io.BytesIO()
        self.reader.write_occupancy_parquet(sample_records, buffer)
        raw_bytes = buffer.getvalue()
        self.assertGreater(len(raw_bytes), 0)

        # Đọc từ raw bytes
        records_from_bytes = self.reader.read_occupancy_parquet(raw_bytes)
        self.assertEqual(len(records_from_bytes), 1)
        self.assertEqual(records_from_bytes[0]["area_id"], "lot-buffer-01")
        self.assertEqual(records_from_bytes[0]["occupied_slots"], 30)

        # Đọc từ BytesIO instance
        buffer.seek(0)
        records_from_io = self.reader.read_occupancy_parquet(buffer)
        self.assertEqual(len(records_from_io), 1)
        self.assertEqual(records_from_io[0]["area_id"], "lot-buffer-01")

    def test_extract_occupancy_with_aliases_and_derivation(self):
        """Kiểm tra khả năng tương thích với các alias cột khác nhau (parking_lot_id, capacity, %)."""
        # Tạo trực tiếp qua PyArrow Table để giả lập file xuất từ các hệ thống khác nhau
        table = pa.Table.from_pydict(
            {
                "parking_lot_id": ["lot-legacy-01", "lot-legacy-01"],
                "datetime_iso": ["2026-10-15T08:00:00Z", "2026-10-15T09:00:00Z"],
                "capacity": [80, 80],
                "occupancy_percent": [75.0, 90.0],  # Dạng phần trăm > 1.0
            }
        )
        file_path = self.test_dir / "legacy_schema.parquet"
        pq.write_table(table, file_path)

        records = self.reader.read_occupancy_parquet(file_path)
        self.assertEqual(len(records), 2)

        # Kiểm tra chuẩn hóa alias
        r1 = records[0]
        self.assertEqual(r1["area_id"], "lot-legacy-01")
        self.assertEqual(r1["total_slots"], 80)
        self.assertAlmostEqual(r1["occupancy_ratio"], 0.75, places=4)
        self.assertEqual(r1["occupied_slots"], 60)  # 80 * 0.75 = 60
        self.assertEqual(r1["hour_of_day"], 8)

        r2 = records[1]
        self.assertAlmostEqual(r2["occupancy_ratio"], 0.90, places=4)
        self.assertEqual(r2["occupied_slots"], 72)  # 80 * 0.90 = 72

    def test_derive_occupancy_ratio_when_missing_ratio(self):
        """Kiểm tra tự tính toán occupancy_ratio khi chỉ có occupied_slots và total_slots."""
        table = pa.Table.from_pydict(
            {
                "area_id": ["lot-calc-01"],
                "timestamp": [1700000000],
                "occupied_slots": [25],
                "total_slots": [50],
            }
        )
        file_path = self.test_dir / "calc_schema.parquet"
        pq.write_table(table, file_path)

        records = self.reader.read_occupancy_parquet(file_path)
        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0]["occupancy_ratio"], 0.50, places=4)

    def test_fallback_when_file_not_found_or_not_loaded(self):
        """Kiểm tra tự động fallback về dữ liệu telemetry baseline khi file chưa nạp/không tồn tại."""
        missing_path = self.test_dir / "not_yet_ingested.parquet"
        self.assertFalse(missing_path.exists())

        # Mặc định fallback_on_error=True
        records = self.reader.read_occupancy_parquet(missing_path, area_id="area-fallback-01")
        self.assertGreater(len(records), 0)
        # 7 ngày x 24 giờ = 168 bản ghi
        self.assertEqual(len(records), 168)
        self.assertTrue(all(r["is_fallback"] for r in records))
        self.assertEqual(records[0]["area_id"], "area-fallback-01")

        # Đảm bảo các trường chuẩn hóa đầy đủ
        first = records[0]
        self.assertIn("area_id", first)
        self.assertIn("timestamp", first)
        self.assertIn("occupied_slots", first)
        self.assertIn("total_slots", first)
        self.assertIn("occupancy_ratio", first)
        self.assertGreater(first["total_slots"], 0)
        self.assertTrue(0.0 <= first["occupancy_ratio"] <= 1.0)

    def test_fallback_when_buffer_or_file_is_empty(self):
        """Kiểm tra fallback khi buffer rỗng (0 bytes) hoặc file rỗng."""
        # 1. Empty bytes
        records_empty_bytes = self.reader.read_occupancy_parquet(b"")
        self.assertEqual(len(records_empty_bytes), 168)
        self.assertTrue(records_empty_bytes[0]["is_fallback"])

        # 2. Empty BytesIO
        records_empty_io = self.reader.read_occupancy_parquet(io.BytesIO())
        self.assertEqual(len(records_empty_io), 168)

        # 3. File rỗng 0 bytes
        empty_file = self.test_dir / "empty.parquet"
        empty_file.touch()
        records_empty_file = self.reader.read_occupancy_parquet(empty_file)
        self.assertEqual(len(records_empty_file), 168)

        # 4. Parquet table rỗng (0 rows)
        empty_table = pa.Table.from_pydict({"area_id": [], "timestamp": []})
        zero_row_file = self.test_dir / "zero_rows.parquet"
        pq.write_table(empty_table, zero_row_file)
        records_zero_rows = self.reader.read_occupancy_parquet(zero_row_file)
        self.assertEqual(len(records_zero_rows), 168)

    def test_fallback_on_error_false_raises_datalake_error(self):
        """Khi fallback_on_error=False, file không tồn tại phải ném DataLakeError."""
        missing_path = self.test_dir / "strict_missing.parquet"
        with self.assertRaises(DataLakeError):
            self.reader.read_occupancy_parquet(missing_path, fallback_on_error=False)

    def test_read_directory_aggregates_multiple_partitions(self):
        """Kiểm tra đọc gom nhiều partition file trong một thư mục data lake."""
        dir_path = self.test_dir / "gold_lake"
        dir_path.mkdir(parents=True)

        rec1 = [{"area_id": "lot-dir", "timestamp": 1700000000, "occupied_slots": 10, "total_slots": 100, "occupancy_ratio": 0.1}]
        rec2 = [{"area_id": "lot-dir", "timestamp": 1700003600, "occupied_slots": 20, "total_slots": 100, "occupancy_ratio": 0.2}]

        self.reader.write_occupancy_parquet(rec1, dir_path / "part_1.parquet")
        self.reader.write_occupancy_parquet(rec2, dir_path / "part_2.parquet")

        combined = self.reader.read_occupancy_parquet(dir_path)
        self.assertEqual(len(combined), 2)
        self.assertEqual(combined[0]["timestamp"], 1700000000)
        self.assertEqual(combined[1]["timestamp"], 1700003600)

    def test_filter_training_dataset_matrix_7x24(self):
        """Kiểm tra tạo ma trận 7 ngày x 24 giờ cho huấn luyện AI chuỗi thời gian."""
        # Dùng baseline để có đầy đủ 168 bản ghi
        baseline_records = self.reader.generate_baseline_telemetry(
            area_id="lot-train-01", total_slots=100
        )
        self.assertEqual(len(baseline_records), 168)

        dataset = self.reader.filter_training_dataset(baseline_records, min_records=10)

        # 1. Ma trận 7x24
        matrix = dataset["matrix_7x24"]
        self.assertEqual(len(matrix), 7)  # 7 ngày (Thứ 2 đến Chủ nhật)
        for dow in range(7):
            self.assertEqual(len(matrix[dow]), 24)  # 24 giờ
            for h in range(24):
                self.assertTrue(0.0 <= matrix[dow][h] <= 1.0)

        # 2. Ma trận số chỗ 7x24
        slots_matrix = dataset["slots_matrix_7x24"]
        self.assertEqual(len(slots_matrix), 7)
        for dow in range(7):
            self.assertEqual(len(slots_matrix[dow]), 24)
            for h in range(24):
                self.assertGreaterEqual(slots_matrix[dow][h], 0)

        # 3. Weekly profile
        profile = dataset["weekly_profile"]
        self.assertIn("weekday_mean", profile)
        self.assertIn("weekend_mean", profile)
        self.assertIn("overall_mean", profile)
        self.assertIn("peak_hour", profile)
        self.assertIn("off_peak_hour", profile)
        self.assertTrue(profile["peak_ratio"] >= profile["off_peak_ratio"])

        # 4. Prophet dataset
        prophet_data = dataset["prophet_dataset"]
        self.assertEqual(len(prophet_data), 168)
        self.assertIn("ds", prophet_data[0])
        self.assertIn("y", prophet_data[0])
        self.assertIsInstance(prophet_data[0]["y"], float)

        # 5. LightGBM dataset
        lgb_data = dataset["lightgbm_dataset"]
        features = lgb_data["features"]
        targets = lgb_data["targets"]
        feature_names = lgb_data["feature_names"]

        self.assertEqual(len(features), 168)
        self.assertEqual(len(targets), 168)
        self.assertEqual(len(feature_names), 8)
        self.assertIn("day_of_week", feature_names)
        self.assertIn("hour_of_day", feature_names)
        self.assertIn("is_weekend", feature_names)
        self.assertIn("hour_sin", feature_names)
        self.assertIn("hour_cos", feature_names)

    def test_filter_training_dataset_fallback_when_sparse(self):
        """Kiểm tra filter_training_dataset tự động bù đắp dữ liệu khi bản ghi ít hơn min_records."""
        sparse_records = [
            {
                "area_id": "lot-sparse-01",
                "timestamp": 1700000000,
                "occupied_slots": 10,
                "total_slots": 100,
                "occupancy_ratio": 0.10,
            }
        ]

        dataset = self.reader.filter_training_dataset(sparse_records, min_records=10)
        self.assertTrue(dataset["is_fallback"])
        # Sau khi fallback, ma trận 7x24 vẫn đầy đủ để không làm crash model training
        self.assertEqual(len(dataset["matrix_7x24"]), 7)
        self.assertEqual(len(dataset["matrix_7x24"][0]), 24)

    def test_to_telemetry_items_integration_with_forecast_service(self):
        """Kiểm tra chuyển đổi sang AreaOccupancyTelemetryItem và nạp vào ForecastService."""
        baseline_records = self.reader.generate_baseline_telemetry(
            area_id="lot-integ-01", total_slots=200
        )
        telemetry_items = self.reader.to_telemetry_items(baseline_records)
        self.assertEqual(len(telemetry_items), 168)
        self.assertEqual(telemetry_items[0].area_id, "lot-integ-01")

        # Nạp vào ForecastService
        service = ForecastService()
        ingested_count = service.ingest_telemetry(telemetry_items)
        self.assertEqual(ingested_count, 168)

        # Kiểm tra tính toán dự báo lấp đầy từ dữ liệu vừa nạp
        ratio, confidence = service.get_projected_occupancy_ratio(
            area_id="lot-integ-01", day_of_week=0, hour_of_day=8
        )
        # Giờ 8 sáng Thứ 2 có baseline là 86%
        self.assertAlmostEqual(ratio, 86.0, delta=1.0)
        self.assertGreaterEqual(confidence, 0.70)


if __name__ == "__main__":
    unittest.main()
