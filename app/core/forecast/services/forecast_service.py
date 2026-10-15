"""Nghiệp vụ Dự Báo Lấp Đầy (Occupancy Forecast) & Đề Xuất Giá Động (Dynamic Tariff).
Đã mở khóa theo quyết định kiến trúc ADR-0037 kết nối ClickHouse Data Marts.
"""
from __future__ import annotations

import os
from pathlib import Path
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.constants import DEFAULT_FORECAST_HOURS, FORECAST_SLOT_SECONDS
from app.core.enums import OccupancyStatus
from app.core.forecast.dtos.forecast_dto import (
    AreaOccupancyForecastResult,
    AreaOccupancyTelemetryItem,
    ForecastSlot,
    OccupancyForecast,
    OccupancyForecastQuery,
    SurgeMultiplierResult,
    TariffRecommendation,
    TariffRecommendationQuery,
)
from app.util.logger import logger


# Biểu đồ phân bổ tỷ lệ lấp đầy chuẩn hóa theo giờ trong ngày cho ngày làm việc (0-4) và cuối tuần (5-6)
_WEEKDAY_HOURLY_BASELINES: Dict[int, float] = {
    0: 18.0, 1: 15.0, 2: 12.0, 3: 10.0, 4: 12.0, 5: 20.0,
    6: 38.0, 7: 68.0, 8: 86.0, 9: 89.0, 10: 84.0, 11: 78.0,
    12: 74.0, 13: 79.0, 14: 83.0, 15: 85.0, 16: 87.0, 17: 91.0,
    18: 93.0, 19: 88.0, 20: 76.0, 21: 58.0, 22: 40.0, 23: 25.0,
}

_WEEKEND_HOURLY_BASELINES: Dict[int, float] = {
    0: 22.0, 1: 16.0, 2: 12.0, 3: 10.0, 4: 10.0, 5: 14.0,
    6: 22.0, 7: 35.0, 8: 52.0, 9: 72.0, 10: 82.0, 11: 87.0,
    12: 85.0, 13: 82.0, 14: 84.0, 15: 88.0, 16: 92.0, 17: 94.0,
    18: 95.0, 19: 92.0, 20: 85.0, 21: 70.0, 22: 50.0, 23: 32.0,
}


class ForecastService:
    """Service dự báo lấp đầy thời gian thực & đề xuất giá động (Dynamic Surge Multiplier).
    
    Tích hợp dữ liệu từ ClickHouse Data Marts (AreaOccupancyTelemetryItem) kết hợp
    chu kỳ tuần (day_of_week 0-6) và giờ trong ngày (hour_of_day 0-23).
    """

    def __init__(
        self,
        datalake_dir: Optional[str | Path] = None,
        lake_reader: Optional[Any] = None,
    ):
        # Cache telemetry: (area_id, day_of_week, hour_of_day) -> AreaOccupancyTelemetryItem
        self._telemetry_cache: Dict[Tuple[str, int, int], AreaOccupancyTelemetryItem] = {}
        self._datalake_dir = Path(datalake_dir) if datalake_dir else None
        self._lake_reader = lake_reader
        self._lake_loaded: bool = False
        self._latest_training_dataset: Optional[Dict[str, Any]] = None

    def ingest_telemetry(self, items: List[AreaOccupancyTelemetryItem]) -> int:
        """Nạp dữ liệu thống kê từ ClickHouse Data Marts hoặc Parquet Data Lake vào telemetry cache."""
        count = 0
        for item in items:
            self.set_telemetry_item(item)
            count += 1
        logger.info(f"ForecastService: Đã nạp {count} telemetry items vào cache.")
        return count

    def set_telemetry_item(self, item: AreaOccupancyTelemetryItem) -> None:
        """Ghi nhận một bản ghi viễn trắc theo (area_id, day_of_week, hour_of_day)."""
        dow = self._normalize_day_of_week(item.day_of_week)
        hour = item.hour_of_day % 24
        key = (item.area_id.strip(), dow, hour)
        self._telemetry_cache[key] = item

    def clear_telemetry(self) -> None:
        """Xóa cache telemetry (dùng cho testing/re-sync)."""
        self._telemetry_cache.clear()
        self._lake_loaded = False
        self._latest_training_dataset = None

    def load_lakehouse_dataset(
        self,
        datalake_dir: Optional[str | Path] = None,
        area_id: Optional[str] = None,
        force_reload: bool = False,
    ) -> Dict[str, Any]:
        """Kiểm tra và nạp dữ liệu Parquet Data Lake (gold/occupancy) làm tập huấn luyện và telemetry cache.

        Args:
            datalake_dir: Đường dẫn thư mục Parquet Lake hoặc None để tự tìm.
            area_id: Lọc theo mã bãi đỗ cụ thể hoặc None để nạp toàn bộ.
            force_reload: Ép nạp lại dù đã nạp trước đó.

        Returns:
            Dict chứa dataset huấn luyện gồm matrix_7x24, weekly_profile, prophet_dataset, lightgbm_dataset.
        """
        if self._lake_loaded and not force_reload and self._latest_training_dataset is not None:
            return self._latest_training_dataset

        from app.core.forecast.readers.parquet_lake_reader import (
            ParquetLakeReader,
            _resolve_default_gold_lake_path,
        )

        target_path = (
            Path(datalake_dir)
            if datalake_dir
            else (self._datalake_dir or _resolve_default_gold_lake_path())
        )
        reader = self._lake_reader or ParquetLakeReader(base_path=target_path)
        self._lake_reader = reader

        # Đọc dữ liệu từ Parquet Lake
        records = reader.read_occupancy_parquet(target_path, area_id=area_id, fallback_on_error=True)
        items = reader.to_telemetry_items(records)
        self.ingest_telemetry(items)

        # Tạo ma trận huấn luyện 7x24 và profile tuần
        training_data = reader.filter_training_dataset(records, min_records=10)
        self._latest_training_dataset = training_data
        self._lake_loaded = True

        logger.info(
            f"ForecastService: Đã nạp Lakehouse dataset thành công từ '{target_path}'. "
            f"Số bản ghi: {len(records)}, số telemetry items: {len(items)}, "
            f"is_fallback={training_data.get('is_fallback')}."
        )
        return training_data

    def _check_and_load_datalake(self, area_id: Optional[str] = None) -> bool:
        """Tự động kiểm tra sự tồn tại của Parquet Lake và nạp viễn trắc thật."""
        if self._lake_loaded:
            return True
        try:
            from app.core.forecast.readers.parquet_lake_reader import _resolve_default_gold_lake_path

            target_path = self._datalake_dir or _resolve_default_gold_lake_path()
            if target_path.exists() and any(target_path.rglob("*.parquet")):
                self.load_lakehouse_dataset(datalake_dir=target_path, area_id=area_id)
                return True
        except Exception as exc:
            logger.warning(f"ForecastService: Không thể tự động nạp Parquet Lake: {exc}")
        self._lake_loaded = True
        return False

    def get_training_dataset(self, area_id: Optional[str] = None) -> Dict[str, Any]:
        """Lấy dataset huấn luyện hiện tại hoặc nạp mới từ Parquet Lake."""
        if self._latest_training_dataset is None or not self._lake_loaded:
            return self.load_lakehouse_dataset(area_id=area_id)
        return self._latest_training_dataset

    def get_matrix_7x24(self, area_id: Optional[str] = None) -> List[List[float]]:
        """Lấy ma trận tỷ lệ lấp đầy 7 ngày x 24 giờ cho mô hình AI."""
        dataset = self.get_training_dataset(area_id=area_id)
        return dataset.get("matrix_7x24", [])

    @staticmethod
    def _normalize_day_of_week(dow: int) -> int:
        """Chuẩn hóa day_of_week về khoảng 0 (Thứ 2) - 6 (Chủ nhật)."""
        if dow == 7:  # ISO Sunday
            return 6
        return max(0, min(6, dow))

    def get_projected_occupancy_ratio(
        self,
        area_id: str,
        day_of_week: int,
        hour_of_day: int,
    ) -> Tuple[float, float]:
        """Tính toán projected_occupancy_ratio (0.0% - 100.0%) và confidence score.
        
        Returns:
            Tuple[projected_occupancy_ratio, confidence_score]
        """
        dow = self._normalize_day_of_week(day_of_week)
        hour = hour_of_day % 24
        key = (area_id.strip(), dow, hour)

        # 1. Nếu cache chưa có và chưa kiểm tra lake, tự động kiểm tra Parquet Lake
        if key not in self._telemetry_cache and not self._lake_loaded:
            self._check_and_load_datalake(area_id=None)

        # 2. Kiểm tra telemetry từ ClickHouse Data Marts hoặc Parquet Lake
        if key in self._telemetry_cache:
            telemetry = self._telemetry_cache[key]
            ratio = telemetry.avg_occupancy_ratio
            # Nếu tỷ lệ lưu dưới dạng thập phân [0.0 - 1.0], nhân 100
            if ratio <= 1.0 and ratio > 0.0:
                ratio = ratio * 100.0
            ratio = max(0.0, min(100.0, ratio))
            confidence = min(0.98, 0.82 + 0.04 * min(telemetry.sample_count, 4))
            return round(ratio, 2), round(confidence, 2)

        # 3. Fallback sang baseline theo chu kỳ ngày trong tuần và giờ
        if dow in (5, 6):  # Thứ 7, Chủ nhật
            ratio = _WEEKEND_HOURLY_BASELINES.get(hour, 50.0)
        else:
            ratio = _WEEKDAY_HOURLY_BASELINES.get(hour, 50.0)

        confidence = 0.85
        return round(max(0.0, min(100.0, ratio)), 2), confidence


    @staticmethod
    def calculate_surge_multiplier(occupancy_ratio: float) -> Tuple[float, str]:
        """Tự động tính toán suggested_surge_multiplier dựa trên tỷ lệ lấp đầy:
        - occupancy >= 85% -> 1.3x - 1.5x
        - 75% <= occupancy < 85% -> 1.15x - 1.25x
        - occupancy < 75% -> 1.0x
        """
        if occupancy_ratio >= 85.0:
            # Nội suy tuyến tính trong khoảng [1.3, 1.5] cho tỷ lệ [85%, 100%]
            fraction = min(1.0, max(0.0, (occupancy_ratio - 85.0) / 15.0))
            multiplier = round(1.30 + fraction * 0.20, 2)
            reason = (
                f"Khu vực có tỷ lệ lấp đầy rất cao ({occupancy_ratio:.1f}% >= 85%), "
                f"tự động áp dụng phụ phí giờ cao điểm {multiplier:.2f}x (1.3x - 1.5x)."
            )
            return multiplier, reason
        elif occupancy_ratio >= 75.0:
            # Nội suy tuyến tính trong khoảng [1.15, 1.25] cho tỷ lệ [75%, 84.9%]
            fraction = min(1.0, max(0.0, (occupancy_ratio - 75.0) / 10.0))
            multiplier = round(1.15 + fraction * 0.10, 2)
            reason = (
                f"Khu vực có tỷ lệ lấp đầy vừa phải ({occupancy_ratio:.1f}%: 75% - 84%), "
                f"áp dụng hệ số phụ phí linh hoạt {multiplier:.2f}x (1.15x - 1.25x)."
            )
            return multiplier, reason
        else:
            multiplier = 1.0
            reason = (
                f"Tỷ lệ lấp đầy bình thường ({occupancy_ratio:.1f}% < 75%), "
                f"áp dụng mức giá tiêu chuẩn 1.0x."
            )
            return multiplier, reason

    @staticmethod
    def _status_from_ratio(ratio: float) -> OccupancyStatus:
        if ratio >= 90.0:
            return OccupancyStatus.CRITICAL
        elif ratio >= 75.0:
            return OccupancyStatus.HIGH
        elif ratio >= 50.0:
            return OccupancyStatus.MEDIUM
        return OccupancyStatus.LOW

    # ──────────────────────────────────────────────────────────────────────────
    # Giao diện gRPC (ForecastService gRPC handler gọi)
    # ──────────────────────────────────────────────────────────────────────────

    def get_occupancy_forecast(self, query: OccupancyForecastQuery) -> OccupancyForecast:
        """Tạo danh sách ForecastSlot cho các khung giờ kế tiếp."""
        base_ts = query.target_timestamp if query.target_timestamp > 0 else int(time.time())
        hours = max(1, query.forecast_hours or DEFAULT_FORECAST_HOURS)
        total_slots = hours * 2  # mỗi slot 30 phút

        slots: List[ForecastSlot] = []
        confidences: List[float] = []
        capacity = query.total_capacity if (query.total_capacity is not None and query.total_capacity > 0) else 100

        for i in range(total_slots):
            slot_ts = base_ts + i * FORECAST_SLOT_SECONDS
            dt = datetime.fromtimestamp(slot_ts, tz=timezone.utc)
            dow = dt.weekday()
            hour = dt.hour

            ratio, conf = self.get_projected_occupancy_ratio(query.parking_lot_id, dow, hour)
            free_spots = max(0, int(capacity * (1.0 - ratio / 100.0)))
            status = self._status_from_ratio(ratio)

            slots.append(
                ForecastSlot(
                    timestamp=slot_ts,
                    predicted_occupancy_percent=ratio,
                    estimated_free_spots=free_spots,
                    status_level=status,
                )
            )
            confidences.append(conf)

        avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.85
        return OccupancyForecast(
            parking_lot_id=query.parking_lot_id,
            slots=slots,
            confidence_score=avg_confidence,
        )

    def get_dynamic_tariff_recommendation(
        self, query: TariffRecommendationQuery
    ) -> TariffRecommendation:
        """Đề xuất hệ số giá động theo thời gian thực cho bãi đỗ."""
        now_dt = datetime.now(timezone.utc)
        dow = now_dt.weekday()
        hour = now_dt.hour

        ratio, _ = self.get_projected_occupancy_ratio(query.parking_lot_id, dow, hour)
        multiplier, reason = self.calculate_surge_multiplier(ratio)

        logger.info(
            f"ForecastService: TariffRecommendation lot={query.parking_lot_id} "
            f"ratio={ratio}% multiplier={multiplier}x"
        )
        return TariffRecommendation(
            parking_lot_id=query.parking_lot_id,
            recommended_multiplier=multiplier,
            reason=reason,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Giao diện REST API (ForecastController gọi)
    # ──────────────────────────────────────────────────────────────────────────

    def predict_area_occupancy(
        self,
        area_id: str,
        target_timestamp: Optional[int] = None,
        forecast_hours: int = DEFAULT_FORECAST_HOURS,
        total_capacity: int = 100,
    ) -> AreaOccupancyForecastResult:
        """Dự báo tỷ lệ lấp đầy thời gian thực cho một parking area."""
        ts = target_timestamp if (target_timestamp and target_timestamp > 0) else int(time.time())
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        dow = dt.weekday()
        hour = dt.hour

        ratio, conf = self.get_projected_occupancy_ratio(area_id, dow, hour)
        free_spots = max(0, int(total_capacity * (1.0 - ratio / 100.0)))
        status = self._status_from_ratio(ratio)

        # Lấy forecast slots cho các giờ tiếp theo với đúng total_capacity
        forecast = self.get_occupancy_forecast(
            OccupancyForecastQuery(
                parking_lot_id=area_id,
                target_timestamp=ts,
                forecast_hours=forecast_hours,
                total_capacity=total_capacity,
            )
        )

        return AreaOccupancyForecastResult(
            area_id=area_id,
            target_timestamp=ts,
            day_of_week=dow,
            hour_of_day=hour,
            projected_occupancy_ratio=ratio,
            status_level=status,
            estimated_free_spots=free_spots,
            confidence_score=conf,
            slots=forecast.slots,
        )

    def get_surge_quote(
        self,
        area_id: str,
        base_hourly_rate: float = 10000.0,
        target_timestamp: Optional[int] = None,
    ) -> SurgeMultiplierResult:
        """Tính toán hệ số giá động và biểu giá thực tế cho parking area."""
        ts = target_timestamp if (target_timestamp and target_timestamp > 0) else int(time.time())
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        dow = dt.weekday()
        hour = dt.hour

        ratio, _ = self.get_projected_occupancy_ratio(area_id, dow, hour)
        multiplier, reason = self.calculate_surge_multiplier(ratio)
        adjusted_rate = round(base_hourly_rate * multiplier, 2)

        return SurgeMultiplierResult(
            area_id=area_id,
            projected_occupancy_ratio=ratio,
            suggested_surge_multiplier=multiplier,
            base_hourly_rate=base_hourly_rate,
            adjusted_hourly_rate=adjusted_rate,
            reason=reason,
        )


forecast_service = ForecastService()
