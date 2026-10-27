"""End-to-End integration test: Parquet Data Lake -> ParquetLakeReader -> ForecastService (ADR-0037 & ADR-0038).

Kiểm thử trọn vẹn luồng dữ liệu Lakehouse:
1. File Parquet xuất thực tế trên ổ đĩa theo phân vùng Hive (`gold/occupancy/year=YYYY/month=MM/`).
2. `ParquetLakeReader` phát hiện, đọc và chuẩn hóa dữ liệu viễn trắc thật (`is_fallback=False`).
3. `ForecastService` nạp dataset viễn trắc vào telemetry cache & xây dựng ma trận huấn luyện 7x24.
4. Tính toán chính xác Projected Occupancy Ratio & Hệ số Surge Multiplier theo các khung giờ cao điểm và thấp điểm.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone

# Đảm bảo đường dẫn module 'ai' được nạp vào sys.path
_AI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

import pyarrow as pa
import pyarrow.parquet as pq

from app.core.enums import OccupancyStatus
from app.core.forecast.dtos.forecast_dto import OccupancyForecastQuery, TariffRecommendationQuery
from app.core.forecast.engines.parquet_lake_reader import ParquetLakeReader
from app.infra.datalake.parquet_occupancy_store import _resolve_default_gold_lake_path
from app.core.forecast.services.forecast_service import ForecastService


@unittest.skipUnless(os.environ.get("AI_RUN_REAL_LAKEHOUSE_TESTS") == "1",
                         "Requires explicitly authorized real lakehouse data; not an offline unit fixture")
class LakehouseForecastE2ETest(unittest.TestCase):
    """Kiểm thử tích hợp End-to-End từ Parquet Lake đến ForecastService."""

    @classmethod
    def setUpClass(cls):
        # Xác định đường dẫn thư mục Gold Occupancy Lake thực tế
        cls.real_lake_dir = _resolve_default_gold_lake_path()

    def setUp(self):
        self.service = ForecastService(datalake_dir=self.real_lake_dir)
        self.service.clear_telemetry()
        self.reader = ParquetLakeReader(base_path=self.real_lake_dir)

    def test_01_real_parquet_files_and_hive_partitions_on_disk(self):
        """Kiểm tra sự tồn tại của file Parquet và phân vùng chuẩn Hive trên ổ đĩa."""
        self.assertTrue(
            self.real_lake_dir.exists(),
            f"Thư mục Parquet Lake '{self.real_lake_dir}' phải tồn tại trên ổ đĩa.",
        )
        parquet_files = list(self.real_lake_dir.rglob("*.parquet"))
        self.assertGreater(
            len(parquet_files),
            0,
            f"Phải có ít nhất một file .parquet trong '{self.real_lake_dir}'.",
        )

        for pf in parquet_files:
            self.assertGreater(pf.stat().st_size, 0, f"File {pf} không được có kích thước 0 bytes.")
            # Kiểm tra phân vùng chuẩn Hive year=YYYY/month=MM
            posix_path = pf.as_posix()
            self.assertIn("year=", posix_path, f"Đường dẫn {pf} phải chứa partition 'year='.")
            self.assertIn("month=", posix_path, f"Đường dẫn {pf} phải chứa partition 'month='.")

            # Kiểm tra schema PyArrow của file
            table = pq.read_table(pf)
            col_names = table.column_names
            self.assertIn("date_actual", col_names)
            self.assertIn("hour_of_day", col_names)
            self.assertIn("area_key", col_names)
            self.assertIn("avg_occupancy_rate", col_names)
            self.assertGreater(table.num_rows, 0)

    def test_02_parquet_lake_reader_extracts_real_telemetry(self):
        """Kiểm tra ParquetLakeReader nạp thành công các bản ghi thực tế từ đĩa với is_fallback=False."""
        records = self.reader.read_occupancy_parquet()
        self.assertGreaterEqual(len(records), 24, "Tập dữ liệu phải có ít nhất 24 giờ viễn trắc.")
        
        # Đảm bảo dữ liệu đọc là dữ liệu thực, không phải fallback
        self.assertFalse(
            records[0]["is_fallback"],
            "Bản ghi nạp từ Parquet Lake trên đĩa phải có is_fallback=False.",
        )

        # Kiểm tra đầy đủ các trường chuẩn hóa
        sample = records[0]
        self.assertIn("area_id", sample)
        self.assertIn("timestamp", sample)
        self.assertIn("occupied_slots", sample)
        self.assertIn("total_slots", sample)
        self.assertIn("occupancy_ratio", sample)
        self.assertIn("day_of_week", sample)
        self.assertIn("hour_of_day", sample)
        self.assertIn("datetime_iso", sample)

        # Kiểm tra danh sách các area_id có mặt trong dữ liệu
        distinct_areas = {r["area_id"] for r in records}
        self.assertIn("area-zone-a", distinct_areas)

    def test_03_parquet_lake_reader_filters_by_specific_area(self):
        """Kiểm tra đọc và lọc riêng biệt theo từng area_id."""
        zone_a_records = self.reader.read_occupancy_parquet(area_id="area-zone-a")
        self.assertEqual(len(zone_a_records), 24, "Khu vực 'area-zone-a' phải có 24 bản ghi theo 24 giờ.")
        self.assertTrue(all(r["area_id"] == "area-zone-a" for r in zone_a_records))
        self.assertTrue(all(not r["is_fallback"] for r in zone_a_records))

        # Kiểm tra các giờ trải đủ từ 0 đến 23
        hours = sorted(r["hour_of_day"] for r in zone_a_records)
        self.assertEqual(hours, list(range(24)))

    def test_04_training_dataset_matrix_7x24_generation(self):
        """Kiểm tra chuẩn bị ma trận 7x24 và profile tuần phục vụ huấn luyện mô hình AI."""
        records = self.reader.read_occupancy_parquet()
        dataset = self.reader.filter_training_dataset(records, min_records=10)

        # Ma trận 7x24
        matrix = dataset["matrix_7x24"]
        self.assertEqual(len(matrix), 7, "Ma trận phải có đúng 7 hàng (7 ngày trong tuần).")
        for dow in range(7):
            self.assertEqual(len(matrix[dow]), 24, f"Hàng ngày {dow} phải có đúng 24 cột (24 giờ).")
            for h in range(24):
                val = matrix[dow][h]
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)

        # Profile tuần
        profile = dataset["weekly_profile"]
        self.assertIn("weekday_mean", profile)
        self.assertIn("weekend_mean", profile)
        self.assertIn("overall_mean", profile)
        self.assertIn("peak_hour", profile)
        self.assertIn("off_peak_hour", profile)

        # Dataset định dạng Prophet và LightGBM
        self.assertGreater(len(dataset["prophet_dataset"]), 0)
        self.assertGreater(len(dataset["lightgbm_dataset"]["features"]), 0)

    def test_05_forecast_service_e2e_ingestion_and_occupancy_calculation(self):
        """Kiểm tra ForecastService nạp Parquet Lake và tính toán tỷ lệ lấp đầy chính xác."""
        # Nạp trực tiếp dataset từ Parquet Lake vào ForecastService
        dataset = self.service.load_lakehouse_dataset(area_id="area-zone-a")
        self.assertFalse(dataset["is_fallback"])
        self.assertGreater(dataset["total_records"], 0)

        # Lấy ngày trong tuần của dữ liệu thực
        sample_records = self.reader.read_occupancy_parquet(area_id="area-zone-a")
        target_dow = sample_records[0]["day_of_week"]

        # 1. Khung giờ cao điểm buổi chiều (Hour 17): tỷ lệ lấp đầy ~88%
        ratio_17, conf_17 = self.service.get_projected_occupancy_ratio("area-zone-a", target_dow, 17)
        self.assertAlmostEqual(ratio_17, 88.0, delta=1.0)
        self.assertGreaterEqual(conf_17, 0.85)

        # 2. Khung giờ cao điểm buổi sáng (Hour 8): tỷ lệ lấp đầy ~82%
        ratio_8, conf_8 = self.service.get_projected_occupancy_ratio("area-zone-a", target_dow, 8)
        self.assertAlmostEqual(ratio_8, 82.0, delta=1.0)

        # 3. Khung giờ thấp điểm đêm (Hour 0): tỷ lệ lấp đầy ~25%
        ratio_0, conf_0 = self.service.get_projected_occupancy_ratio("area-zone-a", target_dow, 0)
        self.assertAlmostEqual(ratio_0, 25.0, delta=1.0)

    def test_06_e2e_surge_multiplier_pricing_tiers(self):
        """Kiểm tra hệ số Surge Multiplier theo 3 phân tầng tỷ lệ lấp đầy từ dữ liệu Lakehouse thực tế."""
        self.service.load_lakehouse_dataset()
        sample_records = self.reader.read_occupancy_parquet(area_id="area-zone-a")
        target_dow = sample_records[0]["day_of_week"]

        # Phân tầng 1: Giờ cao điểm lớn (Hour 17: 88% >= 85%) -> Multiplier nằm trong [1.3x, 1.5x]
        ratio_high, _ = self.service.get_projected_occupancy_ratio("area-zone-a", target_dow, 17)
        mult_high, reason_high = self.service.calculate_surge_multiplier(ratio_high)
        self.assertGreaterEqual(mult_high, 1.30)
        self.assertLessEqual(mult_high, 1.50)
        self.assertIn(">= 85%", reason_high)

        # Phân tầng 2: Giờ cao điểm vừa (Hour 8: 82% thuộc [75%, 84%]) -> Multiplier nằm trong [1.15x, 1.25x]
        ratio_med, _ = self.service.get_projected_occupancy_ratio("area-zone-a", target_dow, 8)
        mult_med, reason_med = self.service.calculate_surge_multiplier(ratio_med)
        self.assertGreaterEqual(mult_med, 1.15)
        self.assertLessEqual(mult_med, 1.25)
        self.assertIn("75% - 84%", reason_med)

        # Phân tầng 3: Giờ thấp điểm (Hour 0: 25% < 75%) -> Multiplier chuẩn 1.0x
        ratio_low, _ = self.service.get_projected_occupancy_ratio("area-zone-a", target_dow, 0)
        mult_low, reason_low = self.service.calculate_surge_multiplier(ratio_low)
        self.assertEqual(mult_low, 1.0)
        self.assertIn("< 75%", reason_low)

    def test_07_e2e_surge_quote_and_area_forecast_apis(self):
        """Kiểm tra get_surge_quote và predict_area_occupancy trả kết quả nhất quán với dữ liệu Lakehouse."""
        # Giả lập thời điểm truy vấn tương ứng với khung giờ cao điểm
        sample_records = self.reader.read_occupancy_parquet(area_id="area-zone-a")
        peak_records = [r for r in sample_records if r["hour_of_day"] == 17]
        self.assertTrue(len(peak_records) > 0)
        peak_ts = peak_records[0]["timestamp"]

        # 1. Kiểm tra báo giá Surge Quote
        quote = self.service.get_surge_quote(
            area_id="area-zone-a",
            base_hourly_rate=20000.0,
            target_timestamp=peak_ts,
        )
        self.assertEqual(quote.area_id, "area-zone-a")
        self.assertAlmostEqual(quote.projected_occupancy_ratio, 88.0, delta=1.0)
        self.assertGreaterEqual(quote.suggested_surge_multiplier, 1.30)
        self.assertGreaterEqual(quote.adjusted_hourly_rate, 26000.0)

        # 2. Kiểm tra dự báo vùng đỗ xe Area Occupancy
        forecast = self.service.predict_area_occupancy(
            area_id="area-zone-a",
            target_timestamp=peak_ts,
            forecast_hours=2,
            total_capacity=200,
        )
        self.assertEqual(forecast.area_id, "area-zone-a")
        self.assertIn(forecast.status_level, [OccupancyStatus.HIGH, OccupancyStatus.CRITICAL])
        self.assertEqual(len(forecast.slots), 4)  # 2 hours * 2 slots



class IsolatedLakehousePipelineTest(unittest.TestCase):
    def test_08_isolated_temporary_lakehouse_pipeline(self):
        """Kiểm tra trọn vẹn luồng Lakehouse trong môi trường cô lập hoàn toàn (Temporary Directory)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_lake = Path(tmp_dir) / "gold" / "occupancy"
            partition_dir = temp_lake / "year=2026" / "month=10"
            partition_dir.mkdir(parents=True)

            # Tạo file Parquet độc lập với schema chuẩn Lakehouse
            table = pa.Table.from_pydict(
                {
                    "date_key": [20261015] * 24,
                    "date_actual": ["2026-10-15"] * 24,
                    "hour_of_day": list(range(24)),
                    "area_key": ["lot-isolated-99"] * 24,
                    "owner_id": ["owner-iso-01"] * 24,
                    "avg_occupancy_rate": [0.30 if h < 7 else 0.86 for h in range(24)],
                    "peak_occupancy_rate": [0.35 if h < 7 else 0.92 for h in range(24)],
                    "total_entries": [20 if h < 7 else 110 for h in range(24)],
                }
            )
            pq.write_table(table, partition_dir / "isolated_data.parquet")

            # Khởi tạo reader và service trỏ vào thư mục cô lập
            iso_reader = ParquetLakeReader(base_path=temp_lake)
            iso_service = ForecastService(datalake_dir=temp_lake, lake_reader=iso_reader)

            # Nạp và kiểm tra
            dataset = iso_service.load_lakehouse_dataset(area_id="lot-isolated-99")
            self.assertFalse(dataset["is_fallback"])
            self.assertEqual(dataset["total_records"], 24)

            # Kiểm tra tính toán Occupancy và Surge Multiplier
            ratio_peak, _ = iso_service.get_projected_occupancy_ratio("lot-isolated-99", day_of_week=3, hour_of_day=10)
            self.assertEqual(ratio_peak, 86.0)
            mult, reason = iso_service.calculate_surge_multiplier(ratio_peak)
            self.assertGreaterEqual(mult, 1.30)
            self.assertIn(">= 85%", reason)


if __name__ == "__main__":
    unittest.main()
