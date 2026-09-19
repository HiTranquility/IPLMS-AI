"""DTO Domain Forecast — dự báo lấp đầy và đề xuất giá động."""
from typing import List

from pydantic import BaseModel

from app.core.constants import DEFAULT_FORECAST_HOURS
from app.core.enums import OccupancyStatus


class OccupancyForecastQuery(BaseModel):
    parking_lot_id: str
    target_timestamp: int
    forecast_hours: int = DEFAULT_FORECAST_HOURS


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
