"""Handler gRPC cho ForecastService (dự báo lấp đầy, đề xuất giá động)."""
import asyncio

from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.forecast_mapper import (
    to_occupancy_forecast_query,
    to_occupancy_forecast_response,
    to_tariff_recommendation_query,
    to_tariff_recommendation_response,
)
from app.core.forecast.services.forecast_service import forecast_service
from app.utils.logger import logger

_, _pb2_grpc = get_stub("forecast_service")


class ForecastHandler(_pb2_grpc.ForecastServiceServicer):
    async def GetOccupancyForecast(self, request, context):
        query = to_occupancy_forecast_query(request)
        logger.info(
            f"ForecastService.GetOccupancyForecast lot={query.parking_lot_id} "
            f"hours={query.forecast_hours}"
        )
        forecast = await asyncio.to_thread(forecast_service.get_occupancy_forecast, query)
        return to_occupancy_forecast_response(forecast)

    async def GetDynamicTariffRecommendation(self, request, context):
        query = to_tariff_recommendation_query(request)
        logger.info(
            f"ForecastService.GetDynamicTariffRecommendation lot={query.parking_lot_id} "
            f"base_rate={query.base_hourly_rate}"
        )
        recommendation = await asyncio.to_thread(
            forecast_service.get_dynamic_tariff_recommendation, query
        )
        return to_tariff_recommendation_response(recommendation)
