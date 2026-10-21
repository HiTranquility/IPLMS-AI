"""REST Controller cho AI Forecast Service — Dự báo lấp đầy & Giá động thời gian thực.
Được mở khóa theo quyết định kiến trúc ADR-0037 kết nối ClickHouse Data Marts.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.constants import DEFAULT_FORECAST_HOURS
from app.core.forecast.dtos.forecast_dto import (
    AreaOccupancyForecastResult,
    SurgeMultiplierResult,
)
from app.core.forecast.services.forecast_service import forecast_service
from app.util.logger import logger

router = APIRouter(tags=["Forecast"])


@router.get("/v1/ai/forecast/occupancy/{area_id}", response_model=AreaOccupancyForecastResult)
@router.get("/forecast/occupancy/{area_id}", response_model=AreaOccupancyForecastResult)
async def get_occupancy_forecast(
    area_id: str,
    target_timestamp: Optional[int] = Query(None, description="Target epoch timestamp (seconds)"),
    hours: int = Query(DEFAULT_FORECAST_HOURS, ge=1, le=48, description="Số giờ dự báo"),
    total_capacity: int = Query(100, ge=1, description="Tổng sức chứa ô đỗ của khu vực"),
) -> AreaOccupancyForecastResult:
    """Lấy dự báo tỷ lệ lấp đầy thời gian thực cho một khu vực đỗ xe.
    
    Kết hợp ClickHouse Data Marts (AreaOccupancyTelemetryItem), day_of_week và hour_of_day.
    """
    if not area_id or not area_id.strip():
        raise HTTPException(status_code=400, detail="area_id không được để trống")

    try:
        result = forecast_service.predict_area_occupancy(
            area_id=area_id.strip(),
            target_timestamp=target_timestamp,
            forecast_hours=hours,
            total_capacity=total_capacity,
        )
        return result
    except Exception as exc:
        logger.error(f"Lỗi khi dự báo lấp đầy cho area={area_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Lỗi dự báo lấp đầy: {str(exc)}")


@router.get("/v1/ai/forecast/surge/{area_id}", response_model=SurgeMultiplierResult)
@router.get("/forecast/surge/{area_id}", response_model=SurgeMultiplierResult)
async def get_surge_multiplier(
    area_id: str,
    base_rate: float = Query(10000.0, ge=0.0, description="Giá giờ cơ bản (VND)"),
    target_timestamp: Optional[int] = Query(None, description="Target epoch timestamp (seconds)"),
) -> SurgeMultiplierResult:
    """Lấy đề xuất hệ số giá động (Surge Multiplier) thời gian thực cho khu vực:
    - occupancy >= 85% -> 1.3x - 1.5x
    - 75% <= occupancy < 85% -> 1.15x - 1.25x
    - occupancy < 75% -> 1.0x
    """
    if not area_id or not area_id.strip():
        raise HTTPException(status_code=400, detail="area_id không được để trống")

    try:
        result = forecast_service.get_surge_quote(
            area_id=area_id.strip(),
            base_hourly_rate=base_rate,
            target_timestamp=target_timestamp,
        )
        return result
    except Exception as exc:
        logger.error(f"Lỗi khi tính toán hệ số giá động cho area={area_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Lỗi tính toán surge multiplier: {str(exc)}")
