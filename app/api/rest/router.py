"""Gom mọi route REST. Thêm route mới → import và include ở đây."""
from fastapi import APIRouter

from app.api.rest.routes.anpr_controller import router as anpr_router
from app.api.rest.routes.copilot_controller import router as copilot_router
from app.api.rest.routes.forecast_controller import router as forecast_router
from app.api.rest.routes.health import router as health_router
from app.api.rest.routes.knowledge_controller import router as knowledge_router
from app.api.rest.routes.system_controller import router as system_router
from app.api.rest.routes.vision_controller import router as vision_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(anpr_router)
api_router.include_router(vision_router)
api_router.include_router(copilot_router)
api_router.include_router(knowledge_router)
api_router.include_router(forecast_router)
api_router.include_router(system_router)
