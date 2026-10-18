"""Compose production REST routes and the opt-in local Vision diagnostics.

Công cụ thử Copilot/nạp tri thức/kiểm cấu hình đã dời vào AI Console (IPLMS ADR-0050).
"""
from fastapi import APIRouter
from app.api.rest.routes.anpr_controller import router as anpr_router
from app.api.rest.routes.health_controller import router as health_router
from app.api.rest.routes.forecast_controller import router as forecast_router
from app.api.rest.routes.vision_controller import router as vision_router

api_router = APIRouter()
for router in (health_router, anpr_router, forecast_router, vision_router):
    api_router.include_router(router)
