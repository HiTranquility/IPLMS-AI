"""Pydantic schemas cho AI Console Vision Lab REST routes."""
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class Sample(BaseModel):
    capture_id: str
    image_sha256: str
    machine_plate: str
    machine_confidence: Optional[float]
    confirmed_plate: str
    human_corrected: bool
    selection_reasons: List[str]
    source_status: str
    purpose: str
    source_final_plate: str
    group_ref: str
    area_ref: str
    captured_at: Optional[str]
    source_updated_at: Optional[str]
    imported_at: Optional[str]


class PendingLabel(BaseModel):
    id: str
    verdict: str
    plate_text: str
    labeler: str
    created_at: str
    quality_flags: List[str] = []


class ReviewItem(Sample):
    label: PendingLabel


class ImportError_(BaseModel):
    capture_id: str
    reason: str
    at: str


class Status(BaseModel):
    sample_count: int
    last_imported_at: Optional[str]
    watermark_at: Optional[str]
    recent_errors: List[ImportError_]
    samples: int
    pending_review: int
    approved: int
    rejected: int


class LabelIn(BaseModel):
    verdict: Literal["CORRECT", "CORRECTED", "UNUSABLE"]
    plate_text: str = Field("", max_length=24)
    quality_flags: List[Literal["blurry", "glare", "skewed", "occluded", "two_line"]] = Field(
        default_factory=list, max_length=5
    )


class DecisionIn(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    note: str = Field("", max_length=500)


class Created(BaseModel):
    id: str


class SeedResult(BaseModel):
    seeded_samples: int
    seeded_reviews: int


class Snapshot(BaseModel):
    id: str
    kind: str
    name: str
    samples_sha256: str
    sample_count: int
    created_by: str
    created_at: str
    frozen_by: str
    frozen_at: Optional[str]


class SnapshotIn(BaseModel):
    kind: Literal["train", "golden"]
    name: str = Field(max_length=120)


class SnapshotCreated(BaseModel):
    id: str
    sample_count: int
    samples_sha256: str


class ReasonIn(BaseModel):
    reason: str = Field(max_length=500)


class ModelIn(BaseModel):
    name: str = Field(max_length=64)
    version: str = Field(max_length=64)
    artifact_key: str = Field(max_length=500)
    sha256: str = Field(max_length=64)
    train_snapshot_id: Optional[str] = Field(None, max_length=36)
    note: str = Field("", max_length=500)


class ModelVersion(BaseModel):
    id: str
    name: str
    version: str
    artifact_key: str
    sha256: str
    train_snapshot_id: str
    stage: str
    note: str
    registered_by: str
    registered_at: str
    proposed_by_id: str
    proposed_by: str
    proposed_at: Optional[str]
    approved_by: str
    approved_at: Optional[str]


class EvalIn(BaseModel):
    snapshot_id: str = Field(max_length=36)


class EvalRun(BaseModel):
    id: str
    kind: str
    snapshot_id: str
    snapshot_name: str
    engine_version: str
    metrics: Optional[dict[str, Any]]
    status: str
    error: str
    started_by: str
    started_at: str
    finished_at: Optional[str]


class Accuracy(BaseModel):
    total: int
    correct: int
    accuracy: Optional[float]
    interval_95: Optional[List[float]]
    target: float
    min_samples: int
    buckets: List[dict[str, Any]]
    curve: List[dict[str, Any]]
    suggested_threshold: Optional[float]
    suggestion_reason: str
    truth_sources: dict[str, int]


class PolicyIn(BaseModel):
    auto_accept_threshold: float = Field(ge=0.5, le=0.99)
    audit_rate: float = Field(ge=0.01, le=0.5)
    reason: str = Field(max_length=500)


class Policy(BaseModel):
    id: str
    model_name: str
    version: int
    auto_accept_threshold: float
    audit_rate: float
    status: str
    evidence: dict[str, Any]
    reason: str
    proposed_by: str
    proposed_by_id: str
    proposed_at: str
    decided_by: str
    decided_at: Optional[str]


class PolicyCreated(BaseModel):
    id: str
    version: int


class Done(BaseModel):
    ok: bool


__all__ = [
    "Accuracy",
    "Created",
    "DecisionIn",
    "Done",
    "EvalIn",
    "EvalRun",
    "ImportError_",
    "LabelIn",
    "ModelIn",
    "ModelVersion",
    "PendingLabel",
    "Policy",
    "PolicyCreated",
    "PolicyIn",
    "ReasonIn",
    "ReviewItem",
    "Sample",
    "SeedResult",
    "Snapshot",
    "SnapshotCreated",
    "SnapshotIn",
    "Status",
]
