"""Copilot Lab trong AI Console: số liệu dùng, lượt chat đã che PII, chấm đúng/sai (P1c)."""
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.rest.console_access import require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.core.console.dtos import ConsoleActor
from app.core.console.services import console_copilot_lab_service
from app.core.copilot.dtos.copilot_dto import UsageSummary

router = APIRouter(prefix="/copilot", tags=["AI Console Copilot Lab"])


class ReviewStats(BaseModel):
    window_days: int
    reviewed: int
    correct: int
    incorrect: int
    unsafe: int
    accuracy: Optional[float]


class TurnReview(BaseModel):
    verdict: str
    note: str
    reviewer: str
    reviewed_at: str


class Turn(BaseModel):
    turn_id: str
    at: str
    task: str
    status: str
    model: str
    prompt_version: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    latency_ms: int
    cost_usd: Optional[float]
    user_role: str
    parking_lot_id: str
    query: str
    answer: str
    error_code: str
    feedback: Optional[int]
    review: Optional[TurnReview]


class Review(BaseModel):
    verdict: Literal["CORRECT", "INCORRECT", "UNSAFE"]
    note: str = Field("", max_length=500)


class Reviewed(BaseModel):
    turn_id: str
    verdict: str


@router.get("/usage", response_model=BaseResponse[UsageSummary])
async def usage(
    days: int = Query(7, ge=1, le=90),
    actor: ConsoleActor = Depends(require_permission("ai:metrics:read")),
) -> BaseResponse[UsageSummary]:
    return BaseResponse.ok([await console_copilot_lab_service.usage_summary(actor, days)], "OK")


@router.get("/review-stats", response_model=BaseResponse[ReviewStats])
async def review_stats(
    days: int = Query(7, ge=1, le=90),
    actor: ConsoleActor = Depends(require_permission("ai:metrics:read")),
) -> BaseResponse[ReviewStats]:
    stats = await console_copilot_lab_service.review_stats(actor, days)
    return BaseResponse.ok([ReviewStats(**stats)], "OK")


@router.get("/turns", response_model=BaseResponse[Turn])
async def turns(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    feedback: Optional[int] = Query(None),
    before: Optional[str] = Query(None, max_length=40),
    actor: ConsoleActor = Depends(require_permission("ai:chatlog:read")),
) -> BaseResponse[Turn]:
    rows = await console_copilot_lab_service.list_turns(actor, limit, status, feedback, before)
    return BaseResponse.ok([Turn(**r) for r in rows], "OK")


@router.post("/turns/{turn_id}/review", response_model=BaseResponse[Reviewed])
async def review(
    turn_id: str, payload: Review,
    actor: ConsoleActor = Depends(require_permission("ai:label:approve")),
) -> BaseResponse[Reviewed]:
    await console_copilot_lab_service.review_turn(actor, turn_id, payload.verdict, payload.note)
    return BaseResponse.ok([Reviewed(turn_id=turn_id, verdict=payload.verdict)], "Đã chấm lượt này.")
