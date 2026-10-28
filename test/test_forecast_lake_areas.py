"""ai bug-028: id bãi phải khớp `area_key` của Gold lake, và nguồn số đi kèm mọi kết quả forecast."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from app.api.grpc.mappers.forecast_mapper import (
    to_occupancy_forecast_response,
    to_tariff_recommendation_response,
)
from app.core.console.dtos import ConsoleActor
from app.core.console.services.tools_service import ConsoleToolsService
from app.core.forecast.dtos.forecast_dto import OccupancyForecastQuery, TariffRecommendationQuery
from app.core.forecast.engines.parquet_lake_reader import ParquetLakeReader
from app.core.forecast.services.forecast_service import ForecastService

ANALYST = ConsoleActor("m-an", frozenset({"ai_analyst"}))
LAKE_AREA = "area-zone-a"
# Id cứng cũ của UI (`ui/src/constants/parkingLots.ts`), không có trong lake.
UI_LOT = "lot_landmark_81"
# 2026-10-15 là thứ Năm (day_of_week=3), trùng ngày có dữ liệu trong lake tạm.
THURSDAY_08H = int(datetime(2026, 10, 15, 8, tzinfo=timezone.utc).timestamp())


def write_lake(root: Path) -> Path:
    lake = root / "gold" / "occupancy"
    part = lake / "year=2026" / "month=10"
    part.mkdir(parents=True)
    table = pa.Table.from_pydict(
        {
            "date_key": [20261015] * 24,
            "date_actual": ["2026-10-15"] * 24,
            "hour_of_day": list(range(24)),
            "area_key": [LAKE_AREA] * 24,
            "avg_occupancy_rate": [0.30 if h < 7 else 0.86 for h in range(24)],
        }
    )
    pq.write_table(table, part / "occupancy.parquet")
    return lake


class ForecastLakeAreaTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.lake = write_lake(Path(self._tmp.name))
        self.svc = ForecastService(datalake_dir=self.lake, lake_reader=ParquetLakeReader(base_path=self.lake))

    def tearDown(self):
        self._tmp.cleanup()

    def test_danh_sach_bai_lay_tu_lake_khong_tu_danh_sach_cung(self):
        self.assertEqual([{"area_id": LAKE_AREA, "records": 24}], self.svc.list_lake_areas())

    def test_lake_rong_thi_khong_co_bai_nao(self):
        with tempfile.TemporaryDirectory() as empty:
            svc = ForecastService(datalake_dir=Path(empty), lake_reader=ParquetLakeReader(base_path=Path(empty)))
            self.assertEqual([], svc.list_lake_areas())

    async def test_simulator_chon_bai_tu_danh_sach_thi_chay_tren_du_lieu_lake(self):
        tools = ConsoleToolsService(store=None, copilot=None, ingestion=None)
        with patch("app.core.console.services.tools_service.forecast_service", self.svc), patch(
            "app.core.console.services.tools_service._resolve_default_gold_lake_path", return_value=self.lake
        ):
            listed = await tools.list_forecast_areas(ANALYST)
            area_id = listed["areas"][0]["area_id"]
            real = await tools.simulate_forecast(ANALYST, area_id=area_id, day_of_week=3)
            baseline = await tools.simulate_forecast(ANALYST, area_id=UI_LOT, day_of_week=3)
        self.assertFalse(real["stage3_inference"]["is_fallback"])
        self.assertEqual("profile-7x24", real["stage3_inference"]["model_version"])
        self.assertTrue(baseline["stage3_inference"]["is_fallback"])

    def test_bai_ngoai_lake_khong_bi_gan_nhan_lake_sau_khi_nap(self):
        # Trước đây bản ghi baseline tự sinh lọt vào cache nên lần hỏi sau trả `lakehouse_parquet`.
        self.svc.load_lakehouse_dataset(area_id=UI_LOT, force_reload=True)
        result = self.svc.predict_area_occupancy(UI_LOT, target_timestamp=THURSDAY_08H)
        self.assertTrue(result.is_fallback)
        self.assertEqual("heuristic_baseline", result.data_source)

    def test_grpc_forecast_mang_nguon_so(self):
        real = self.svc.get_occupancy_forecast(
            OccupancyForecastQuery(parking_lot_id=LAKE_AREA, target_timestamp=THURSDAY_08H, forecast_hours=2)
        )
        self.assertEqual(("lakehouse_parquet", False), (real.data_source, real.is_fallback))
        msg = to_occupancy_forecast_response(real)
        self.assertEqual(("lakehouse_parquet", False), (msg.data_source, msg.is_fallback))

        baseline = self.svc.get_occupancy_forecast(
            OccupancyForecastQuery(parking_lot_id=UI_LOT, target_timestamp=THURSDAY_08H, forecast_hours=2)
        )
        self.assertEqual(("heuristic_baseline", True), (baseline.data_source, baseline.is_fallback))

    def test_grpc_de_xuat_gia_mang_nguon_so(self):
        rec = self.svc.get_dynamic_tariff_recommendation(
            TariffRecommendationQuery(parking_lot_id=UI_LOT, base_hourly_rate=10000)
        )
        msg = to_tariff_recommendation_response(rec)
        self.assertEqual(("heuristic_baseline", True), (msg.data_source, msg.is_fallback))


if __name__ == "__main__":
    unittest.main()
