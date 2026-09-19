"""DTO Domain Copilot — hỏi đáp RAG và phân xử tranh chấp."""
from typing import List, Optional

from pydantic import BaseModel

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


class AnswerChunk(BaseModel):
    token: str
    is_finished: bool
    sources: List[str] = []


class DisputeArbitrationRequest(BaseModel):
    dispute_id: str
    session_id: str
    claim_reason: str
    claimed_amount: float


class DisputeVerdict(BaseModel):
    verdict: ArbitrationVerdict
    recommended_refund: float
    justification: str
    evidence_urls: List[str] = []
