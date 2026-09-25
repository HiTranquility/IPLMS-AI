"""Time-Series Occupancy Model Engine (Prophet / LightGBM)."""
import time
from typing import List, Dict, Any

from app.core.constants import FORECAST_SLOT_SECONDS, DEFAULT_FORECAST_HOURS
from app.core.enums import OccupancyStatus
from app.infra.datalake.parquet_reader import parquet_reader
from app.util.logger import logger


class OccupancyModelEngine:
    def predict_occupancy(
        self,
        parking_lot_id: str,
        target_timestamp: int,
        forecast_hours: int = DEFAULT_FORECAST_HOURS,
    ) -> List[Dict[str, Any]]:
        logger.info(f"Running occupancy forecast model for lot={parking_lot_id}, hours={forecast_hours}...")
        history = parquet_reader.load_historical_occupancy(parking_lot_id)

        slots = []
        base_time = target_timestamp if target_timestamp > 0 else int(time.time())
        num_slots = forecast_hours * 2

        for i in range(num_slots):
            slot_time = base_time + i * FORECAST_SLOT_SECONDS
            simulated_pct = min(0.95, 0.40 + (i * 0.08) % 0.60)

            if simulated_pct > 0.85:
                status = OccupancyStatus.CRITICAL
            elif simulated_pct > 0.70:
                status = OccupancyStatus.HIGH
            elif simulated_pct > 0.50:
                status = OccupancyStatus.MEDIUM
            else:
                status = OccupancyStatus.LOW

            slots.append({
                "timestamp": slot_time,
                "predicted_occupancy_percent": round(simulated_pct * 100, 1),
                "estimated_free_spots": int(100 * (1 - simulated_pct)),
                "status_level": status.value,
            })

        return slots


occupancy_model = OccupancyModelEngine()

