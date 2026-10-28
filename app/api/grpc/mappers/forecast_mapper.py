"""Map message protobuf ↔ DTO Domain Forecast."""
from app.api.grpc.generated_stubs import get_stub
from app.core.forecast.constants import DEFAULT_FORECAST_HOURS
from app.core.forecast.dtos.forecast_dto import (
    OccupancyForecast,
    OccupancyForecastQuery,
    TariffRecommendation,
    TariffRecommendationQuery,
)

_pb2, _ = get_stub("forecast_service")


def to_occupancy_forecast_query(message) -> OccupancyForecastQuery:
    return OccupancyForecastQuery(
        parking_lot_id=message.parking_lot_id,
        target_timestamp=message.target_timestamp,
        forecast_hours=message.forecast_hours or DEFAULT_FORECAST_HOURS,
    )


def to_tariff_recommendation_query(message) -> TariffRecommendationQuery:
    return TariffRecommendationQuery(
        parking_lot_id=message.parking_lot_id,
        base_hourly_rate=message.base_hourly_rate,
    )


def to_occupancy_forecast_response(forecast: OccupancyForecast):
    return _pb2.OccupancyForecastResponse(
        parking_lot_id=forecast.parking_lot_id,
        slots=[
            _pb2.ForecastSlot(
                timestamp=slot.timestamp,
                predicted_occupancy_percent=slot.predicted_occupancy_percent,
                estimated_free_spots=slot.estimated_free_spots,
                status_level=_pb2.OccupancyStatus.Value(slot.status_level),
            )
            for slot in forecast.slots
        ],
        confidence_score=forecast.confidence_score,
        data_source=forecast.data_source,
        is_fallback=forecast.is_fallback,
    )


def to_tariff_recommendation_response(recommendation: TariffRecommendation):
    return _pb2.TariffRecommendationResponse(
        parking_lot_id=recommendation.parking_lot_id,
        recommended_multiplier=recommendation.recommended_multiplier,
        reason=recommendation.reason,
        data_source=recommendation.data_source,
        is_fallback=recommendation.is_fallback,
    )
