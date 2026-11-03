"""Vision trong AI Console: gán nhãn, duyệt, snapshot, model, accept policy (ISSUE-126 P3–P5).

Quyền cần step-up (`ai:golden:freeze`, `ai:model:promote`, `ai:policy:threshold`)
đi qua `require_permission` — cổng đó tự đòi TOTP gần đây (ADR-0048 §4).
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.rest.console_access import require_any_permission, require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.api.rest.schemas.console_vision_schema import (
    Accuracy,
    Created,
    DecisionIn,
    Done,
    EvalIn,
    EvalRun,
    ImportError_,
    LabelIn,
    ModelIn,
    ModelVersion,
    PendingLabel,
    Policy,
    PolicyCreated,
    PolicyIn,
    ReasonIn,
    ReviewItem,
    Sample,
    SeedResult,
    Snapshot,
    SnapshotCreated,
    SnapshotIn,
    Status,
)
from app.core.console import (
    ConsoleActor,
    accept_policy_service,
    model_lab_service,
    vision_lab_service,
)

router = APIRouter(prefix="/vision", tags=["AI Console vision"])


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
    return BaseResponse.ok([Status(**await vision_lab_service.status(actor))], "OK")


@router.post("/seed-demo", response_model=BaseResponse[SeedResult])
async def seed_demo(actor: ConsoleActor = Depends(require_any_permission("ai:task:label", "ai:label:approve", "ai:member:manage"))):
    result = await vision_lab_service.seed_demo_samples(actor, reset=True)
    return BaseResponse.ok([SeedResult(**result)], f"Đã nạp {result['seeded_samples']} mẫu thực hành.")


@router.get("/queue", response_model=BaseResponse[Sample])
async def label_queue(
    limit: int = Query(20, ge=1, le=100),
    actor: ConsoleActor = Depends(require_permission("ai:task:label")),
):
    rows = await vision_lab_service.label_queue(actor, limit)
    return BaseResponse.ok([Sample(**r) for r in rows], "OK")


@router.get("/samples/{capture_id}/crop")
async def crop(
    capture_id: str,
    _: ConsoleActor = Depends(require_any_permission("ai:task:label", "ai:label:approve")),
) -> Response:
    image = await vision_lab_service.crop(capture_id)
    if image is None:
        return Response(status_code=404)
    # Ảnh biển số là PII: không cache (middleware đặt no-store), không cho nhúng chỗ khác.
    return Response(content=image, media_type=_image_type(image))


@router.post("/samples/{capture_id}/labels", response_model=BaseResponse[Created])
async def add_label(
    capture_id: str, payload: LabelIn,
    actor: ConsoleActor = Depends(require_permission("ai:task:label")),
):
    label_id = await vision_lab_service.add_label(
        actor, capture_id, payload.verdict, payload.plate_text, payload.quality_flags
    )
    return BaseResponse.ok([Created(id=label_id)], "Đã gán nhãn — chờ người khác duyệt.")


@router.get("/reviews", response_model=BaseResponse[ReviewItem])
async def review_queue(
    limit: int = Query(20, ge=1, le=100),
    actor: ConsoleActor = Depends(require_permission("ai:label:approve")),
):
    rows = await vision_lab_service.review_queue(actor, limit)
    return BaseResponse.ok([ReviewItem(**r) for r in rows], "OK")


@router.post("/labels/{label_id}/decision", response_model=BaseResponse[Done])
async def decide_label(
    label_id: str, payload: DecisionIn,
    actor: ConsoleActor = Depends(require_permission("ai:label:approve")),
):
    await vision_lab_service.decide(actor, label_id, payload.decision, payload.note)
    return BaseResponse.ok([Done(ok=True)], "Đã duyệt." if payload.decision == "APPROVED" else "Đã trả lại.")


@router.get("/snapshots", response_model=BaseResponse[Snapshot])
async def snapshots(
    actor: ConsoleActor = Depends(require_any_permission("ai:dataset:snapshot", "ai:model:evaluate")),
):
    rows = await vision_lab_service.list_snapshots(actor)
    return BaseResponse.ok([Snapshot(**r) for r in rows], "OK")


@router.post("/snapshots", response_model=BaseResponse[SnapshotCreated])
async def create_snapshot(
    payload: SnapshotIn, actor: ConsoleActor = Depends(require_permission("ai:dataset:snapshot")),
):
    created = await vision_lab_service.create_snapshot(actor, payload.kind, payload.name)
    return BaseResponse.ok([SnapshotCreated(**created)], "Đã tạo snapshot.")


@router.post("/snapshots/{snapshot_id}/freeze", response_model=BaseResponse[Done])
async def freeze_snapshot(
    snapshot_id: str, payload: ReasonIn,
    actor: ConsoleActor = Depends(require_permission("ai:golden:freeze")),
):
    await vision_lab_service.freeze(actor, snapshot_id, payload.reason)
    return BaseResponse.ok([Done(ok=True)], "Đã khoá golden.")


# ── P4: model + eval ─────────────────────────────────────────────────────────

@router.get("/models", response_model=BaseResponse[ModelVersion])
async def models(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    rows = await model_lab_service.list_models(actor)
    return BaseResponse.ok([ModelVersion(**r) for r in rows], "OK")


@router.post("/models", response_model=BaseResponse[Created])
async def register_model(
    payload: ModelIn, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
):
    model_id = await model_lab_service.register(actor, payload.model_dump())
    return BaseResponse.ok([Created(id=model_id)], "Đã đăng ký model.")


@router.post("/models/{model_id}/propose", response_model=BaseResponse[Done])
async def propose_model(
    model_id: str, payload: ReasonIn,
    actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
):
    await model_lab_service.propose(actor, model_id, payload.reason)
    return BaseResponse.ok([Done(ok=True)], "Đã đề xuất — chờ AI Lead khác duyệt.")


@router.post("/models/{model_id}/promote", response_model=BaseResponse[Done])
async def promote_model(
    model_id: str, payload: ReasonIn,
    actor: ConsoleActor = Depends(require_permission("ai:model:promote")),
):
    await model_lab_service.promote(actor, model_id, payload.reason)
    return BaseResponse.ok([Done(ok=True)], "Đã đưa model lên production.")


@router.get("/evals", response_model=BaseResponse[EvalRun])
async def evals(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    rows = await model_lab_service.list_evals(actor)
    return BaseResponse.ok([EvalRun(**r) for r in rows], "OK")


@router.post("/evals", response_model=BaseResponse[Created])
async def start_eval(
    payload: EvalIn, actor: ConsoleActor = Depends(require_permission("ai:model:evaluate")),
):
    run_id = await model_lab_service.start_eval(actor, payload.snapshot_id)
    return BaseResponse.ok([Created(id=run_id)], "Đã bắt đầu đo.")


# ── P5: accept policy ────────────────────────────────────────────────────────

@router.get("/accuracy", response_model=BaseResponse[Accuracy])
async def accuracy(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    report = await accept_policy_service.accuracy(actor)
    return BaseResponse.ok([Accuracy(**report)], "OK")


@router.get("/policies", response_model=BaseResponse[Policy])
async def policies(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    rows = await accept_policy_service.list_policies(actor)
    return BaseResponse.ok([Policy(**r) for r in rows], "OK")


@router.post("/policies", response_model=BaseResponse[PolicyCreated])
async def propose_policy(
    payload: PolicyIn, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
):
    created = await accept_policy_service.propose(
        actor, payload.auto_accept_threshold, payload.audit_rate, payload.reason
    )
    return BaseResponse.ok([PolicyCreated(**created)], "Đã đề xuất ngưỡng — chờ AI Lead khác duyệt.")


@router.post("/policies/{policy_id}/decision", response_model=BaseResponse[Done])
async def decide_policy(
    policy_id: str, payload: DecisionIn,
    actor: ConsoleActor = Depends(require_permission("ai:policy:threshold")),
):
    await accept_policy_service.decide(actor, policy_id, payload.decision, payload.note)
    return BaseResponse.ok([Done(ok=True)], "Đã quyết ngưỡng.")
