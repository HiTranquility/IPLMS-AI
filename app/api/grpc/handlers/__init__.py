"""1 proto service = 1 handler. Handler chỉ điều phối: map request, gọi service, map response."""
from app.api.grpc.handlers.copilot_handler import CopilotHandler
from app.api.grpc.handlers.forecast_handler import ForecastHandler
from app.api.grpc.handlers.health_handler import HealthHandler
from app.api.grpc.handlers.vision_handler import VisionHandler

__all__ = ["VisionHandler", "CopilotHandler", "ForecastHandler", "HealthHandler"]
