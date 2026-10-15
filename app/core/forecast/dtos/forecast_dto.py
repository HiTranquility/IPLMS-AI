"""DTO Domain Forecast — dự báo lấp đầy và đề xuất giá động."""
from typing import List, Optional

from pydantic import BaseModel

from app.core.constants import DEFAULT_FORECAST_HOURS
from app.core.enums import OccupancyStatus


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


class SurgeMultiplierResult(BaseModel):
    """Kết quả đề xuất giá động / surge multiplier cho REST API."""
    area_id: str
    projected_occupancy_ratio: float  # 0.0 - 100.0 (%)
    suggested_surge_multiplier: float  # 1.0x, 1.15x - 1.25x, hoặc 1.3x - 1.5x
    base_hourly_rate: float
    adjusted_hourly_rate: float
    reason: str
