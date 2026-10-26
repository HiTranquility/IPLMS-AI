"""DTO Domain Forecast — dự báo lấp đầy và đề xuất giá động."""
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.core.constants import DEFAULT_FORECAST_HOURS
from app.core.enums import OccupancyStatus

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


class OccupancyForecastQuery(BaseModel):
    parking_lot_id: str
    target_timestamp: int
    forecast_hours: int = DEFAULT_FORECAST_HOURS
    total_capacity: Optional[int] = None


class TariffRecommendationQuery(BaseModel):
    parking_lot_id: str
    base_hourly_rate: float


class ForecastSlot(BaseModel):
    timestamp: int
    predicted_occupancy_percent: float
    estimated_free_spots: int
    status_level: OccupancyStatus


class OccupancyForecast(BaseModel):
    parking_lot_id: str
    slots: List[ForecastSlot]
    confidence_score: float


class TariffRecommendation(BaseModel):
    parking_lot_id: str
    recommended_multiplier: float
    reason: str


class AreaOccupancyTelemetryItem(BaseModel):
    """Telemetry aggregate từ ClickHouse Data Marts (agg_owner_occupancy_hourly)."""
    area_id: str
    day_of_week: int  # 0-6 (0=Thứ hai, 6=Chủ nhật)
    hour_of_day: int  # 0-23
    avg_occupancy_ratio: float  # 0.0 - 1.0 hoặc 0.0 - 100.0%
    peak_occupancy_ratio: float = 0.0
    total_capacity: int = 100
    sample_count: int = 1


class AreaOccupancyForecastResult(BaseModel):
    """Kết quả dự báo lấp đầy thời gian thực cho REST API."""
    area_id: str
    target_timestamp: int
    day_of_week: int
    hour_of_day: int
    projected_occupancy_ratio: float  # 0.0 - 100.0 (%)
    status_level: OccupancyStatus
    estimated_free_spots: int
    confidence_score: float
    slots: List[ForecastSlot] = []
    data_source: str = "heuristic_baseline"
    is_fallback: bool = False


class SurgeMultiplierResult(BaseModel):
    """Kết quả đề xuất giá động / surge multiplier cho REST API."""
    area_id: str
    projected_occupancy_ratio: float  # 0.0 - 100.0 (%)
    suggested_surge_multiplier: float  # 1.0x, 1.15x - 1.25x, hoặc 1.3x - 1.5x
    base_hourly_rate: float
    adjusted_hourly_rate: float
    reason: str
    data_source: str = "heuristic_baseline"
    is_fallback: bool = False

