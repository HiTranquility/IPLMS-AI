"""Pydantic schemas cho Vision & Anti-Fraud REST routes."""
from typing import Optional

from pydantic import BaseModel


class VerifyMatchRequest(BaseModel):
    expected_vehicle_type: str
    current_vehicle_type: str
    checkin_crop_url: Optional[str] = ""
    checkout_crop_url: Optional[str] = ""


class VerifyMatchResponse(BaseModel):
    is_matched: bool
    similarity_score: float
    mismatch_reason: str


__all__ = [
    "VerifyMatchRequest",
    "VerifyMatchResponse",
]
