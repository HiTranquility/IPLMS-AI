"""Healthcheck, liveness, and readiness probe endpoints (REST controller)."""
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "iplms-ai"}


@router.get("/health/live")
def health_live() -> dict:
    return {"status": "ok", "live": True, "service": "iplms-ai"}


@router.get("/health/ready")
def health_ready() -> dict:
    return {"status": "ok", "ready": True, "service": "iplms-ai"}
