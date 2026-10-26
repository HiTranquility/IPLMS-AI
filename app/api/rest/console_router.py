"""Gom route của AI Console — tách khỏi `router.py` của process inference (ADR-0048 §1)."""
from fastapi import APIRouter, Depends

from app.api.rest.console_access import require_same_origin_write
from app.api.rest.routes.console_auth_controller import router as auth_router
from app.api.rest.routes.console_copilot_controller import router as copilot_router
from app.api.rest.routes.console_member_controller import router as member_router
from app.api.rest.routes.console_tools_controller import router as tools_router
from app.api.rest.routes.console_vision_controller import router as vision_router

console_router = APIRouter(dependencies=[Depends(require_same_origin_write)])
for router in (auth_router, member_router, copilot_router, vision_router, tools_router):
    console_router.include_router(router)

__all__ = ["console_router"]
