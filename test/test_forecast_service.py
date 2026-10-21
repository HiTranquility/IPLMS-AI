"""Unit tests for AI Forecast Service (ADR-0037).
Tests occupancy forecasting, ClickHouse telemetry ingestion, surge multiplier logic,
gRPC mapper/service methods, and REST controller endpoints.
"""
import os
import sys
import unittest
from datetime import datetime, timezone

# Ensure 'ai' root is on sys.path for direct python -m unittest runs
_AI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

from fastapi.testclient import TestClient

from app.core.constants import DEFAULT_FORECAST_HOURS
from app.core.enums import OccupancyStatus
from app.core.forecast.dtos.forecast_dto import (
    AreaOccupancyTelemetryItem,
    OccupancyForecastQuery,
    TariffRecommendationQuery,
)
from app.core.forecast.services.forecast_service import ForecastService, forecast_service
from app.main import app


class TestForecastOccupancyAndSurgeLogic(unittest.TestCase):
    def setUp(self):
        self.service = ForecastService()

    def test_baseline_occupancy_bounded_between_0_and_100(self):
        """Kiểm tra tỷ lệ lấp đầy theo chu kỳ ngày và giờ luôn nằm trong [0%, 100%]."""
        for dow in range(7):
            for hour in range(24):
                ratio, conf = self.service.get_projected_occupancy_ratio("lot-test", dow, hour)
                self.assertGreaterEqual(ratio, 0.0)
                self.assertLessEqual(ratio, 100.0)
                self.assertGreaterEqual(conf, 0.50)
                self.assertLessEqual(conf, 1.0)

    def test_provenance_and_detail_fallback(self):
        """Kiểm tra provenance data_source và is_fallback khi fallback sang heuristic."""
        detail = self.service.get_projected_occupancy_ratio_detail("lot-nonexistent-999", 2, 14)
        self.assertIn("data_source", detail)
        self.assertIn("is_fallback", detail)
        self.assertEqual(detail["data_source"], "heuristic_baseline")
        self.assertTrue(detail["is_fallback"])
        self.assertEqual(detail["confidence"], 0.55)


    def test_status_from_ratio(self):
        """Kiểm tra ánh xạ ngưỡng lấp đầy sang OccupancyStatus enum."""
        self.assertEqual(self.service._status_from_ratio(95.0), OccupancyStatus.CRITICAL)
        self.assertEqual(self.service._status_from_ratio(90.0), OccupancyStatus.CRITICAL)
        self.assertEqual(self.service._status_from_ratio(85.0), OccupancyStatus.HIGH)
        self.assertEqual(self.service._status_from_ratio(75.0), OccupancyStatus.HIGH)
        self.assertEqual(self.service._status_from_ratio(60.0), OccupancyStatus.MEDIUM)
        self.assertEqual(self.service._status_from_ratio(50.0), OccupancyStatus.MEDIUM)
        self.assertEqual(self.service._status_from_ratio(30.0), OccupancyStatus.LOW)

    def test_surge_multiplier_high_occupancy_gte_85(self):
        """Kiểm tra surge multiplier khi occupancy >= 85% nằm trong khoảng [1.3x, 1.5x]."""
        # Ngưỡng thấp nhất của dải cao điểm: 85% -> 1.30x
        m85, r85 = self.service.calculate_surge_multiplier(85.0)
        self.assertEqual(m85, 1.30)
        self.assertIn(">= 85%", r85)
        self.assertIn("1.3x - 1.5x", r85)

        # Mức giữa dải cao điểm: 92.5% -> 1.40x
        m92, r92 = self.service.calculate_surge_multiplier(92.5)
        self.assertEqual(m92, 1.40)

        # Mức trần: 100% -> 1.50x
        m100, r100 = self.service.calculate_surge_multiplier(100.0)
        self.assertEqual(m100, 1.50)

    def test_surge_multiplier_moderate_occupancy_75_to_84(self):
        """Kiểm tra surge multiplier khi 75% <= occupancy < 85% nằm trong khoảng [1.15x, 1.25x]."""
        # Ngưỡng thấp nhất của dải vừa phải: 75% -> 1.15x
        m75, r75 = self.service.calculate_surge_multiplier(75.0)
        self.assertEqual(m75, 1.15)
        self.assertIn("75% - 84%", r75)
        self.assertIn("1.15x - 1.25x", r75)

        # Mức giữa: 80% -> 1.20x
        m80, r80 = self.service.calculate_surge_multiplier(80.0)
        self.assertEqual(m80, 1.20)

        # Cận trên: 84.9%
        m84, _ = self.service.calculate_surge_multiplier(84.9)
        self.assertGreaterEqual(m84, 1.15)
        self.assertLessEqual(m84, 1.25)

    def test_surge_multiplier_normal_occupancy_lt_75(self):
        """Kiểm tra surge multiplier khi occupancy < 75% giữ nguyên 1.0x chuẩn."""
        m74, r74 = self.service.calculate_surge_multiplier(74.9)
        self.assertEqual(m74, 1.0)
        self.assertIn("< 75%", r74)
        self.assertIn("1.0x", r74)

        m50, _ = self.service.calculate_surge_multiplier(50.0)
        self.assertEqual(m50, 1.0)

        m0, _ = self.service.calculate_surge_multiplier(0.0)
        self.assertEqual(m0, 1.0)


class TestClickHouseTelemetryIntegration(unittest.TestCase):
    def setUp(self):
        self.service = ForecastService()
        self.service.clear_telemetry()

    def test_telemetry_item_ingestion_and_lookup(self):
        """Kiểm tra nạp telemetry item từ ClickHouse marts và tra cứu chính xác."""
        item = AreaOccupancyTelemetryItem(
            area_id="area-vincom-01",
            day_of_week=2,  # Thứ 4
            hour_of_day=14,  # 14:00
            avg_occupancy_ratio=88.5,
            peak_occupancy_ratio=94.0,
            sample_count=10,
        )
        self.service.set_telemetry_item(item)

        ratio, conf = self.service.get_projected_occupancy_ratio("area-vincom-01", 2, 14)
        self.assertEqual(ratio, 88.5)
        self.assertGreaterEqual(conf, 0.90)  # Có nhiều mẫu nên confidence cao

        # Kiểm tra tỷ lệ dạng số thập phân 0.885 được tự động chuyển thành 88.5%
        item_decimal = AreaOccupancyTelemetryItem(
            area_id="area-vincom-02",
            day_of_week=0,
            hour_of_day=9,
            avg_occupancy_ratio=0.78,
            sample_count=5,
        )
        self.service.set_telemetry_item(item_decimal)
        ratio_dec, _ = self.service.get_projected_occupancy_ratio("area-vincom-02", 0, 9)
        self.assertEqual(ratio_dec, 78.0)

    def test_iso_sunday_normalization(self):
        """Kiểm tra day_of_week = 7 (ISO Sunday) được chuẩn hóa về 6."""
        item = AreaOccupancyTelemetryItem(
            area_id="area-sunday",
            day_of_week=7,
            hour_of_day=18,
            avg_occupancy_ratio=96.0,
        )
        self.service.set_telemetry_item(item)
        ratio, _ = self.service.get_projected_occupancy_ratio("area-sunday", 6, 18)
        self.assertEqual(ratio, 96.0)

    def test_bulk_ingest_telemetry(self):
        """Kiểm tra hàm nạp hàng loạt telemetry items."""
        items = [
            AreaOccupancyTelemetryItem(area_id="bulk-01", day_of_week=1, hour_of_day=8, avg_occupancy_ratio=82.0),
            AreaOccupancyTelemetryItem(area_id="bulk-01", day_of_week=1, hour_of_day=9, avg_occupancy_ratio=91.0),
        ]
        count = self.service.ingest_telemetry(items)
        self.assertEqual(count, 2)

        r8, _ = self.service.get_projected_occupancy_ratio("bulk-01", 1, 8)
        r9, _ = self.service.get_projected_occupancy_ratio("bulk-01", 1, 9)
        self.assertEqual(r8, 82.0)
        self.assertEqual(r9, 91.0)


class TestGrpcForecastMethods(unittest.TestCase):
    def setUp(self):
        self.service = ForecastService()

    def test_get_occupancy_forecast_returns_slots(self):
        """Kiểm tra hàm get_occupancy_forecast trả về đủ số slot theo forecast_hours."""
        query = OccupancyForecastQuery(
            parking_lot_id="lot-test-grpc",
            target_timestamp=1700000000,
            forecast_hours=4,
        )
        result = self.service.get_occupancy_forecast(query)
        self.assertEqual(result.parking_lot_id, "lot-test-grpc")
        # 4 giờ x 2 slot/giờ = 8 slots
        self.assertEqual(len(result.slots), 8)
        self.assertGreater(result.confidence_score, 0.0)

        for slot in result.slots:
            self.assertGreaterEqual(slot.predicted_occupancy_percent, 0.0)
            self.assertLessEqual(slot.predicted_occupancy_percent, 100.0)
            self.assertGreaterEqual(slot.estimated_free_spots, 0)
            self.assertIn(slot.status_level, list(OccupancyStatus))

    def test_get_dynamic_tariff_recommendation(self):
        """Kiểm tra hàm get_dynamic_tariff_recommendation trả về multiplier và reason hợp lệ."""
        query = TariffRecommendationQuery(
            parking_lot_id="lot-dynamic-tariff",
            base_hourly_rate=15000.0,
        )
        recommendation = self.service.get_dynamic_tariff_recommendation(query)
        self.assertEqual(recommendation.parking_lot_id, "lot-dynamic-tariff")
    def test_capacity_consistency_bug_036(self):
        """Kiểm tra bug-036: Capacity nhất quán giữa tổng và từng slot khi capacity != 100."""
        capacity = 150
        res = self.service.predict_area_occupancy(
            area_id="area-cap-test",
            forecast_hours=2,
            total_capacity=capacity,
        )
        self.assertGreater(len(res.slots), 0)

        # Kiểm tra slot đầu tiên khớp với tỷ lệ và capacity
        first_slot = res.slots[0]
        expected_free = max(0, int(capacity * (1.0 - first_slot.predicted_occupancy_percent / 100.0)))
        self.assertEqual(
            first_slot.estimated_free_spots,
            expected_free,
            f"Slot free spots ({first_slot.estimated_free_spots}) phải khớp với capacity {capacity} (expected {expected_free})",
        )
        # Kiểm tra không bị tính theo mẫu số 100
        if first_slot.predicted_occupancy_percent < 80.0:
            self.assertNotEqual(
                first_slot.estimated_free_spots,
                max(0, int(100 * (1.0 - first_slot.predicted_occupancy_percent / 100.0))),
                "Slot không được bị tính theo hardcoded capacity 100!",
            )


class TestForecastRestController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_get_occupancy_forecast_endpoint(self):
        """Kiểm tra endpoint GET /v1/ai/forecast/occupancy/{area_id}."""
        response = self.client.get("/v1/ai/forecast/occupancy/area-e2e-01?hours=3&total_capacity=150")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["area_id"], "area-e2e-01")
        self.assertIn("projected_occupancy_ratio", data)
        self.assertIn("status_level", data)
        self.assertIn("estimated_free_spots", data)
        self.assertIn("confidence_score", data)
        self.assertEqual(len(data["slots"]), 6)  # 3 hours * 2 slots

    def test_get_surge_multiplier_endpoint(self):
        """Kiểm tra endpoint GET /v1/ai/forecast/surge/{area_id}."""
        response = self.client.get("/v1/ai/forecast/surge/area-e2e-01?base_rate=20000")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["area_id"], "area-e2e-01")
        self.assertIn("suggested_surge_multiplier", data)
        self.assertIn("base_hourly_rate", data)
        self.assertEqual(data["base_hourly_rate"], 20000.0)
        self.assertIn("adjusted_hourly_rate", data)
        self.assertIn("reason", data)

    def test_api_prefix_compatibility(self):
        """Kiểm tra cả đường dẫn có prefix /api/v1/ai/forecast/ cũng hoạt động bình thường."""
        res_occ = self.client.get("/api/v1/ai/forecast/occupancy/area-compat")
        self.assertEqual(res_occ.status_code, 200)

        res_surge = self.client.get("/api/v1/ai/forecast/surge/area-compat")
        self.assertEqual(res_surge.status_code, 200)


if __name__ == "__main__":
    unittest.main()
