"""Small local-only diagnostics; never expose credentials, URLs or file paths."""
from fastapi import APIRouter, Depends
from app.api.rest.developer_access import require_developer_access
from app.config import get_config

router = APIRouter(prefix="/system", tags=["Developer diagnostics"],
                   dependencies=[Depends(require_developer_access)])


@router.get("/info")
async def get_system_info() -> dict:
    cfg = get_config()
    return {
        "service": "iplms-ai",
        "scope": "local developer diagnostics; not a readiness check",
        "vision_device": cfg.vision.device,
        "grpc_port": cfg.server.grpc_port,
        "rest_port": cfg.server.fastapi_port,
    }
