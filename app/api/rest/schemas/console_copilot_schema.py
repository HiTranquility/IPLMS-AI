"""Pydantic schemas cho AI Console Copilot Lab REST routes."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


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


class PromoteEvalIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    expected_behavior: Literal["ANSWER", "REFUSE"] = "ANSWER"
    category: str = Field("regulation", max_length=64)
    note: str = Field("", max_length=500)


__all__ = [
    "PromoteEvalIn",
    "Review",
    "ReviewStats",
    "Reviewed",
    "Turn",
    "TurnReview",
]
