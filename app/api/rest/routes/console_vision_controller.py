"""Vision trong AI Console: gán nhãn, duyệt, snapshot, model, accept policy (ISSUE-126 P3–P5).

Quyền cần step-up (`ai:golden:freeze`, `ai:model:promote`, `ai:policy:threshold`)
đi qua `require_permission` — cổng đó tự đòi TOTP gần đây (ADR-0048 §4).
"""
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.rest.console_access import require_any_permission, require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.core.console.dtos import ConsoleActor
from app.core.console.services.accept_policy_service import console_accept_policy_service
from app.core.console.services.model_lab_service import console_model_lab_service
from app.core.console.services.vision_lab_service import console_vision_lab_service

router = APIRouter(prefix="/vision", tags=["AI Console vision"])


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


def _image_type(data: bytes) -> str:
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


# ── P3: dữ liệu + nhãn ───────────────────────────────────────────────────────

@router.get("/status", response_model=BaseResponse[Status])
async def status(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    return BaseResponse.ok([Status(**await console_vision_lab_service.status(actor))], "OK")


@router.post("/seed-demo", response_model=BaseResponse[SeedResult])
async def seed_demo(actor: ConsoleActor = Depends(require_any_permission("ai:task:label", "ai:label:approve", "ai:member:manage"))):
    result = await console_vision_lab_service.seed_demo_samples(actor)
    return BaseResponse.ok([SeedResult(**result)], f"Đã nạp {result['seeded_samples']} mẫu thực hành.")


@router.get("/queue", response_model=BaseResponse[Sample])
async def label_queue(
    limit: int = Query(20, ge=1, le=100),
    actor: ConsoleActor = Depends(require_permission("ai:task:label")),
):
    rows = await console_vision_lab_service.label_queue(actor, limit)
    return BaseResponse.ok([Sample(**r) for r in rows], "OK")


@router.get("/samples/{capture_id}/crop")
async def crop(
    capture_id: str,
    _: ConsoleActor = Depends(require_any_permission("ai:task:label", "ai:label:approve")),
) -> Response:
    image = await console_vision_lab_service.crop(capture_id)
    if image is None:
        return Response(status_code=404)
    # Ảnh biển số là PII: không cache (middleware đặt no-store), không cho nhúng chỗ khác.
    return Response(content=image, media_type=_image_type(image))


@router.post("/samples/{capture_id}/labels", response_model=BaseResponse[Created])
async def add_label(
    capture_id: str, payload: LabelIn,
    actor: ConsoleActor = Depends(require_permission("ai:task:label")),
):
    label_id = await console_vision_lab_service.add_label(
        actor, capture_id, payload.verdict, payload.plate_text, payload.quality_flags
    )
    return BaseResponse.ok([Created(id=label_id)], "Đã gán nhãn — chờ người khác duyệt.")


@router.get("/reviews", response_model=BaseResponse[ReviewItem])
async def review_queue(
    limit: int = Query(20, ge=1, le=100),
    actor: ConsoleActor = Depends(require_permission("ai:label:approve")),
):
    rows = await console_vision_lab_service.review_queue(actor, limit)
    return BaseResponse.ok([ReviewItem(**r) for r in rows], "OK")


@router.post("/labels/{label_id}/decision", response_model=BaseResponse[Done])
async def decide_label(
    label_id: str, payload: DecisionIn,
    actor: ConsoleActor = Depends(require_permission("ai:label:approve")),
):
    await console_vision_lab_service.decide(actor, label_id, payload.decision, payload.note)
    return BaseResponse.ok([Done(ok=True)], "Đã duyệt." if payload.decision == "APPROVED" else "Đã trả lại.")


@router.get("/snapshots", response_model=BaseResponse[Snapshot])
async def snapshots(
    actor: ConsoleActor = Depends(require_any_permission("ai:dataset:snapshot", "ai:model:evaluate")),
):
    rows = await console_vision_lab_service.list_snapshots(actor)
    return BaseResponse.ok([Snapshot(**r) for r in rows], "OK")


@router.post("/snapshots", response_model=BaseResponse[SnapshotCreated])
async def create_snapshot(
    payload: SnapshotIn, actor: ConsoleActor = Depends(require_permission("ai:dataset:snapshot")),
):
    created = await console_vision_lab_service.create_snapshot(actor, payload.kind, payload.name)
    return BaseResponse.ok([SnapshotCreated(**created)], "Đã tạo snapshot.")


@router.post("/snapshots/{snapshot_id}/freeze", response_model=BaseResponse[Done])
async def freeze_snapshot(
    snapshot_id: str, payload: ReasonIn,
    actor: ConsoleActor = Depends(require_permission("ai:golden:freeze")),
):
    await console_vision_lab_service.freeze(actor, snapshot_id, payload.reason)
    return BaseResponse.ok([Done(ok=True)], "Đã khoá golden.")


# ── P4: model + eval ─────────────────────────────────────────────────────────

@router.get("/models", response_model=BaseResponse[ModelVersion])
async def models(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    rows = await console_model_lab_service.list_models(actor)
    return BaseResponse.ok([ModelVersion(**r) for r in rows], "OK")


@router.post("/models", response_model=BaseResponse[Created])
async def register_model(
    payload: ModelIn, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
):
    model_id = await console_model_lab_service.register(actor, payload.model_dump())
    return BaseResponse.ok([Created(id=model_id)], "Đã đăng ký model.")


@router.post("/models/{model_id}/propose", response_model=BaseResponse[Done])
async def propose_model(
    model_id: str, payload: ReasonIn,
    actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
):
    await console_model_lab_service.propose(actor, model_id, payload.reason)
    return BaseResponse.ok([Done(ok=True)], "Đã đề xuất — chờ AI Lead khác duyệt.")


@router.post("/models/{model_id}/promote", response_model=BaseResponse[Done])
async def promote_model(
    model_id: str, payload: ReasonIn,
    actor: ConsoleActor = Depends(require_permission("ai:model:promote")),
):
    await console_model_lab_service.promote(actor, model_id, payload.reason)
    return BaseResponse.ok([Done(ok=True)], "Đã đưa model lên production.")


@router.get("/evals", response_model=BaseResponse[EvalRun])
async def evals(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    rows = await console_model_lab_service.list_evals(actor)
    return BaseResponse.ok([EvalRun(**r) for r in rows], "OK")


@router.post("/evals", response_model=BaseResponse[Created])
async def start_eval(
    payload: EvalIn, actor: ConsoleActor = Depends(require_permission("ai:model:evaluate")),
):
    run_id = await console_model_lab_service.start_eval(actor, payload.snapshot_id)
    return BaseResponse.ok([Created(id=run_id)], "Đã bắt đầu đo.")


# ── P5: accept policy ────────────────────────────────────────────────────────

@router.get("/accuracy", response_model=BaseResponse[Accuracy])
async def accuracy(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    report = await console_accept_policy_service.accuracy(actor)
    return BaseResponse.ok([Accuracy(**report)], "OK")


@router.get("/policies", response_model=BaseResponse[Policy])
async def policies(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    rows = await console_accept_policy_service.list_policies(actor)
    return BaseResponse.ok([Policy(**r) for r in rows], "OK")


@router.post("/policies", response_model=BaseResponse[PolicyCreated])
async def propose_policy(
    payload: PolicyIn, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
):
    created = await console_accept_policy_service.propose(
        actor, payload.auto_accept_threshold, payload.audit_rate, payload.reason
    )
    return BaseResponse.ok([PolicyCreated(**created)], "Đã đề xuất ngưỡng — chờ AI Lead khác duyệt.")


@router.post("/policies/{policy_id}/decision", response_model=BaseResponse[Done])
async def decide_policy(
    policy_id: str, payload: DecisionIn,
    actor: ConsoleActor = Depends(require_permission("ai:policy:threshold")),
):
    await console_accept_policy_service.decide(actor, policy_id, payload.decision, payload.note)
    return BaseResponse.ok([Done(ok=True)], "Đã quyết ngưỡng.")
