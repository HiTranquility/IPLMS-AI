"""Compose production REST routes and opt-in local diagnostics."""
from fastapi import APIRouter
from app.api.rest.routes.anpr_controller import router as anpr_router
from app.api.rest.routes.health_controller import router as health_router
from app.api.rest.routes.forecast_controller import router as forecast_router
from app.api.rest.routes.copilot_controller import router as copilot_router
from app.api.rest.routes.knowledge_controller import router as knowledge_router
from app.api.rest.routes.system_controller import router as system_router
from app.api.rest.routes.vision_controller import router as vision_router

api_router = APIRouter()
for router in (health_router, anpr_router, forecast_router, vision_router,
               copilot_router, knowledge_router, system_router):
    api_router.include_router(router)
