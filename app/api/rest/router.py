"""Gom mọi route REST. Thêm route mới → import và include ở đây."""
from fastapi import APIRouter

from app.api.rest.routes.anpr_controller import router as anpr_router
from app.api.rest.routes.forecast_controller import router as forecast_router
from app.api.rest.routes.health_controller import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(anpr_router)
api_router.include_router(forecast_router)
