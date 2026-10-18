"""DTO Domain Copilot — hỏi đáp RAG và phân xử tranh chấp."""
from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.enums import ArbitrationVerdict


class AskQuestionRequest(BaseModel):
    query: str
    user_id: str
    user_role: str = "member"
    parking_lot_id: Optional[str] = None
    session_id: Optional[str] = None


class CopilotAnswer(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    refused: bool = False
    guardrail_triggered: Optional[str] = None
    prompt_version: str = "v2"
    latency_ms: Optional[float] = None


class AnswerChunk(BaseModel):
    token: str
    is_finished: bool
    sources: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    refused: bool = False
    guardrail_triggered: Optional[str] = None
    prompt_version: str = "v2"
    latency_ms: Optional[float] = None


class DisputeArbitrationRequest(BaseModel):
    dispute_id: str
    session_id: str
    claim_reason: str
    claimed_amount: float


class DisputeVerdict(BaseModel):
    verdict: ArbitrationVerdict
    recommended_refund: float
    justification: str
    evidence_urls: List[str] = Field(default_factory=list)
