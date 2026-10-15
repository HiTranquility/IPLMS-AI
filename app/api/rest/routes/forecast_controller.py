"""REST route cho Forecast & Dynamic Tariff Service."""
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.forecast.dtos.forecast_dto import (
    OccupancyForecastQuery,
    TariffRecommendationQuery,
)
from app.core.forecast.services.forecast_service import forecast_service
from app.core.exceptions import FeatureNotImplementedError

router = APIRouter(prefix="/forecast", tags=["Forecast & Pricing"])


class OccupancyQueryPayload(BaseModel):
    parking_lot_id: str = "lot_landmark_81"
    forecast_hours: int = 24


class TariffQueryPayload(BaseModel):
    parking_lot_id: str = "lot_landmark_81"
    base_hourly_rate: float = 35000.0


class SimulationPayload(BaseModel):
    parking_lot_id: str = "lot_landmark_81"
    capacity: int = 250
    base_hourly_rate: float = 35000.0
    surge_threshold: float = 0.85
    surge_multiplier: float = 1.30
    hours: int = 24


@router.post("/occupancy")
async def get_occupancy_forecast(payload: OccupancyQueryPayload) -> Dict[str, Any]:
    """Gọi trực tiếp service dự báo tỷ lệ lấp đầy (tuân thủ quy tắc Thà lỗi hơn bịa)."""
    try:
        import time
        query = OccupancyForecastQuery(
            parking_lot_id=payload.parking_lot_id,
            target_timestamp=int(time.time()),
            forecast_hours=payload.forecast_hours,
        )
        forecast_service.get_occupancy_forecast(query)
        return {"success": True, "data": []}
    except FeatureNotImplementedError as exc:
        return {
            "success": False,
            "status": "UNIMPLEMENTED",
            "message": str(exc),
            "safety_rule": "Thà lỗi hơn bịa (ADR-0008): Hệ thống từ chối trả số giả khi chưa có model ML được huấn luyện trên dữ liệu datalake thật.",
            "guide_link": "docs/guides/04-forecast-training-strategy.md"
        }
    except Exception as exc:
        return {"success": False, "status": "ERROR", "message": str(exc)}


@router.post("/tariff-recommendation")
async def get_tariff_recommendation(payload: TariffQueryPayload) -> Dict[str, Any]:
    """Gọi trực tiếp service đề xuất giá động."""
    try:
        query = TariffRecommendationQuery(
            parking_lot_id=payload.parking_lot_id,
            base_hourly_rate=payload.base_hourly_rate,
        )
        forecast_service.get_dynamic_tariff_recommendation(query)
        return {"success": True, "data": []}
    except FeatureNotImplementedError as exc:
        return {
            "success": False,
            "status": "UNIMPLEMENTED",
            "message": str(exc),
            "safety_rule": "Thà lỗi hơn bịa: Hệ số giá động ảnh hưởng trực tiếp đến hoá đơn của khách nên không được trả hệ số cứng bịa.",
        }
    except Exception as exc:
        return {"success": False, "status": "ERROR", "message": str(exc)}


@router.post("/simulate")
async def simulate_forecast(payload: SimulationPayload) -> Dict[str, Any]:
    """Mô phỏng đường cong dự báo dựa trên chu kỳ ngày/đêm và thuật toán giá động."""
    now = datetime.now()
    forecast_points = []
    
    # Mô phỏng mẫu chu kỳ thực tế bãi xe đô thị (cao điểm 8h-11h sáng và 18h-21h tối)
    for i in range(payload.hours):
        slot_time = now + timedelta(hours=i)
        hour = slot_time.hour
        
        # Mẫu hình chu kỳ đô thị
        if 7 <= hour <= 11:
            base_rate = 0.70 + 0.20 * math.sin((hour - 7) / 4 * math.pi)
        elif 12 <= hour <= 16:
            base_rate = 0.55 + 0.15 * math.sin((hour - 12) / 4 * math.pi)
        elif 17 <= hour <= 21:
            base_rate = 0.75 + 0.22 * math.sin((hour - 17) / 4 * math.pi)
        else:
            base_rate = 0.20 + 0.10 * math.cos((hour) / 6 * math.pi)
            
        occupancy_pct = max(0.10, min(0.98, base_rate))
        occupied_slots = int(occupancy_pct * payload.capacity)
        available_slots = payload.capacity - occupied_slots
        
        is_surge = occupancy_pct >= payload.surge_threshold
        recommended_rate = payload.base_hourly_rate * payload.surge_multiplier if is_surge else payload.base_hourly_rate
        
        forecast_points.append({
            "timestamp": slot_time.strftime("%H:00 (%d/%m)"),
            "hour": hour,
            "occupancy_rate": round(occupancy_pct * 100, 1),
            "occupied_slots": occupied_slots,
            "available_slots": available_slots,
            "is_surge": is_surge,
            "recommended_hourly_rate": round(recommended_rate),
        })

    peak_points = [p for p in forecast_points if p["is_surge"]]
    
    return {
        "success": True,
        "parking_lot_id": payload.parking_lot_id,
        "total_capacity": payload.capacity,
        "base_hourly_rate": payload.base_hourly_rate,
        "surge_threshold_pct": payload.surge_threshold * 100,
        "surge_multiplier": payload.surge_multiplier,
        "peak_hours_count": len(peak_points),
        "forecast_series": forecast_points,
        "model_type": "Simulated Ridge Time-Series Feature Baseline (training/forecast/)"
    }
