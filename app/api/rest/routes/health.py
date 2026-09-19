"""Healthcheck and Liveness probe endpoints."""
from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "iplms-ai"}
