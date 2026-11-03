"""Pydantic schemas cho Copilot REST routes."""
from typing import List, Optional

from pydantic import BaseModel, Field


class AskPayload(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    parking_lot_id: Optional[str] = Field(None, max_length=128)
    user_id: Optional[str] = Field("test-user", max_length=64)


class AskResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    mode: str = "rag_pgvector"
    refused: bool = False
    guardrail_triggered: Optional[str] = None
    prompt_version: str = "v2"
    latency_ms: Optional[float] = None


class DisputePayload(BaseModel):
    dispute_id: str = "DSP-1002"
    session_id: str = "sess-8891"
    claim_reason: str = "Barie không tự động mở, bị tính thêm phí trễ giờ"
    claimed_amount: float = 35000.0


class WorkflowSimulationPayload(BaseModel):
    dispute_id: str = "DSP-1002"
    claim_reason: str = "Barie kẹt lúc ra cổng > 15 phút"
    claimed_amount: float = 35000.0
    has_checkin_snapshot: bool = True
    has_checkout_snapshot: bool = True


__all__ = [
    "AskPayload",
    "AskResponse",
    "DisputePayload",
    "WorkflowSimulationPayload",
]
