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
    # Bản xem trước của scope `parking_lot_id` thay vì bản khách thấy (ISSUE-009).
    # Backend chỉ bật cờ này cho người quản lý đúng scope đó.
    preview: bool = False
    # Tham số thử của Chat Studio trên console (ai bug-017). None = giữ cấu hình mặc định.
    # Chặn biên ở AskIn của console; ở đây chỉ mang giá trị đi tiếp.
    top_k: Optional[int] = None
    min_similarity: Optional[float] = None
    temperature: Optional[float] = None


def tuning_kwargs(request: "AskQuestionRequest") -> dict:
    """Chỉ những tham số thử đã đặt, để caller cũ và pipeline giả trong test giữ chữ ký."""
    names = ("top_k", "min_similarity", "temperature")
    return {name: getattr(request, name) for name in names if getattr(request, name, None) is not None}


class CopilotAnswer(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    model_revision: str = ""
    turn_id: str = ""
    prompt_version: str = ""


class AnswerChunk(BaseModel):
    token: str
    is_finished: bool
    sources: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    refused: bool = False
    guardrail_triggered: Optional[str] = None
    model_revision: str = ""
    turn_id: str = ""          # chỉ có ở chunk cuối
    prompt_version: str = "v2"   # chỉ có ở chunk cuối
    latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    speed_tok_s: Optional[float] = None
    context_tokens: Optional[int] = None
    context_limit: Optional[int] = 4096


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


class UsageDay(BaseModel):
    date: str
    requests: int
    errors: int
    refused: int
    avg_latency_ms: float
    speed_tok_s: Optional[float] = None


class UsageSummary(BaseModel):
    """Tóm tắt mức dùng AI cho dashboard admin (đề Final §6.6, IPLMS ADR-0049)."""

    window_days: int
    total_requests: int
    success_requests: int
    refused_requests: int
    no_context_requests: int
    error_requests: int
    avg_latency_ms: float
    p95_latency_ms: float
    avg_speed_tok_s: Optional[float] = None
    input_tokens: int
    output_tokens: int
    cost_known: bool
    total_cost_usd: float
    avg_cost_usd: float
    thumbs_up: int
    thumbs_down: int
    days: List[UsageDay] = Field(default_factory=list)
