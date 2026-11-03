"""Công cụ thử trong AI Console — thay trang dev `/dashboard` cũ (IPLMS ADR-0050)."""
import json
import time
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.rest.console_access import require_any_permission, require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.api.rest.schemas.console_tools_schema import (
    ASK_BODY_FIELDS,
    AnprClipOut,
    AnprTryOut,
    AskIn,
    ChatMessageIn,
    Check,
    ClipEventOut,
    ComputeSettingsIn,
    DeleteDocOut,
    DocumentChunkItem,
    DocumentChunksOut,
    DocumentVersionItem,
    EngineActionIn,
    EngineStatus,
    ForecastAreasOut,
    ForecastLakeArea,
    ForecastSimulateIn,
    IngestOut,
    KnowledgeDocOut,
    PolicySettingsIn,
    RevokeSessionIn,
    SystemCheck,
    VerifyMatchIn,
    VerifyMatchOut,
)
from app.config import get_config
from app.core.console import ConsoleActor, tools_service
from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES
from app.core.copilot.dtos.copilot_dto import CopilotAnswer
from app.util.logger import logger

router = APIRouter(prefix="/tools", tags=["AI Console tools"])


@router.get("/forecast/areas", response_model=BaseResponse[ForecastAreasOut])
async def forecast_areas(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    result = await tools_service.list_forecast_areas(actor)
    return BaseResponse.ok([ForecastAreasOut(**result)], "Danh sách bãi có dữ liệu trong Gold lake.")


@router.post("/forecast/simulate", response_model=BaseResponse[dict])
async def simulate_forecast(
    payload: ForecastSimulateIn,
    actor: ConsoleActor = Depends(require_permission("ai:metrics:read")),
):
    result = await tools_service.simulate_forecast(
        actor,
        area_id=payload.area_id,
        day_of_week=payload.day_of_week,
        total_capacity=payload.total_capacity,
        base_hourly_rate=payload.base_hourly_rate,
    )
    return BaseResponse.ok([result], "Đã chạy Pipeline 3: Lakehouse Parquet -> LightGBM/Prophet -> Dynamic Surge Tariff.")


@router.get("/system", response_model=BaseResponse[SystemCheck])
async def system(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    return BaseResponse.ok([SystemCheck(**await tools_service.system_check(actor))], "OK")


@router.post("/anpr/recognize", response_model=BaseResponse[AnprTryOut])
async def try_anpr(
    file: UploadFile = File(...),
    lane_id: Optional[str] = Form(None, max_length=128),
    actor: ConsoleActor = Depends(require_permission("ai:model:evaluate")),
):
    image = await file.read(KNOWLEDGE_MAX_FILE_BYTES + 1)
    result = await tools_service.try_anpr(actor, image, lane_id)
    if result.get("crop_image") and not result.get("crop_plate_image_url"):
        result["crop_plate_image_url"] = result["crop_image"]
    return BaseResponse.ok([AnprTryOut(**result)], "Kết quả từ engine ANPR đang nạp (ảnh không được lưu).")


@router.post("/anpr/recognize-clip", response_model=BaseResponse[AnprClipOut])
async def try_anpr_clip(
    file: UploadFile = File(...),
    mode: Literal["interval", "motion"] = Form("interval"),
    actor: ConsoleActor = Depends(require_permission("ai:model:evaluate")),
):
    # Đọc tối đa giới hạn + 1 byte: đủ để service báo "vượt dung lượng" mà không nạp cả file lớn.
    clip = await file.read(get_config().vision.clip_max_bytes + 1)
    started = time.perf_counter()
    result = await tools_service.try_anpr_clip(actor, clip, file.content_type or "", mode == "motion")
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return BaseResponse.ok([AnprClipOut(**result)], "Kết quả đọc clip (clip không được lưu).")


@router.post("/vision/verify-match", response_model=BaseResponse[VerifyMatchOut])
async def verify_match(payload: VerifyMatchIn, actor: ConsoleActor = Depends(require_permission("ai:model:evaluate"))):
    result = await tools_service.verify_match(
        actor, payload.expected_vehicle_type, payload.current_vehicle_type
    )
    return BaseResponse.ok([VerifyMatchOut(**result)], "Đối chiếu theo loại xe; chưa so ảnh.")


@router.get("/knowledge/documents", response_model=BaseResponse[KnowledgeDocOut])
async def knowledge_documents(
    parking_lot_id: Optional[str] = Query(None, max_length=128),
    actor: ConsoleActor = Depends(require_permission("ai:prompt:edit")),
):
    docs = await tools_service.knowledge_documents(actor, parking_lot_id)
    return BaseResponse.ok([KnowledgeDocOut(**d) for d in docs], "OK")


@router.delete("/knowledge/documents/{document_id}", response_model=BaseResponse[DeleteDocOut])
async def delete_knowledge_document(
    document_id: str,
    parking_lot_id: Optional[str] = Query(None, max_length=128),
    actor: ConsoleActor = Depends(require_permission("ai:prompt:edit")),
):
    deleted_count = await tools_service.delete_knowledge_document(actor, document_id, parking_lot_id)
    return BaseResponse.ok([DeleteDocOut(deleted=deleted_count, document_id=document_id)], f"Đã xóa tài liệu {document_id}")


@router.get("/knowledge/documents/{document_id}/chunks", response_model=BaseResponse[DocumentChunksOut])
async def get_document_chunks(
    document_id: str,
    parking_lot_id: Optional[str] = Query(None, max_length=128),
    version_no: int = Query(0, ge=0),
    actor: ConsoleActor = Depends(require_permission("ai:prompt:edit")),
):
    chunks_data = await tools_service.document_chunks(actor, document_id, parking_lot_id, version_no)
    return BaseResponse.ok([DocumentChunksOut(**chunks_data)], "OK")


@router.post("/copilot/stream")
async def try_copilot_stream(payload: AskIn, actor: ConsoleActor = Depends(require_any_permission("ai:prompt:edit", "ai:chatlog:read"))):
    async def event_generator():
        try:
            async for chunk in tools_service.try_copilot_stream(
                actor, payload.query, payload.parking_lot_id, **payload.tuning()
            ):
                data = {
                    "token": chunk.token,
                    "is_finished": chunk.is_finished,
                    "sources": chunk.sources,
                    "citations": getattr(chunk, "citations", []),
                    "confidence": chunk.confidence,
                    "refused": chunk.refused,
                    "guardrail_triggered": chunk.guardrail_triggered,
                    "prompt_version": chunk.prompt_version,
                    "turn_id": chunk.turn_id,
                    "latency_ms": chunk.latency_ms,
                    "speed_tok_s": chunk.speed_tok_s,
                    "input_tokens": chunk.input_tokens,
                    "output_tokens": chunk.output_tokens,
                    "context_tokens": chunk.context_tokens,
                    "context_limit": chunk.context_limit,
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("Error in try_copilot_stream: %s", exc)
            err_data = {
                "token": f"\n\n⚠️ Dịch vụ AI (Embedding/LLM) hiện không khả dụng: {exc}",
                "is_finished": True,
                "sources": [],
                "citations": [],
                "confidence": 0.0,
                "refused": True,
                "guardrail_triggered": "FAILED_RESPONSE",
                "status": "ERROR",
                "prompt_version": "v2",
                "turn_id": None,
                "latency_ms": 0.0,
            }
            yield f"data: {json.dumps(err_data, ensure_ascii=False)}\n\n"
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/copilot", response_model=BaseResponse[CopilotAnswer])
async def try_copilot(payload: AskIn, actor: ConsoleActor = Depends(require_any_permission("ai:prompt:edit", "ai:chatlog:read"))):
    answer = await tools_service.try_copilot(actor, payload.query, payload.parking_lot_id, **payload.tuning())
    return BaseResponse.ok([answer], "Trả lời từ pipeline RAG có guard (lượt thử, không tính vào số sản phẩm).")


@router.post("/knowledge", response_model=BaseResponse[IngestOut])
async def ingest_draft(
    file: UploadFile = File(...),
    document_id: str = Form(..., max_length=36),
    category: str = Form("regulation", max_length=128),
    parking_lot_id: Optional[str] = Form(None, max_length=128),
    actor: ConsoleActor = Depends(require_permission("ai:prompt:edit")),
):
    content = await file.read(KNOWLEDGE_MAX_FILE_BYTES + 1)
    if len(content) > KNOWLEDGE_MAX_FILE_BYTES:
        raise ValueError("Tệp vượt 8 MB.")
    result = await tools_service.ingest_draft(
        actor, document_id, file.filename or "", content, category, parking_lot_id
    )
    out = IngestOut(**result)
    if not out.ok:
        # Cùng envelope lỗi của console; embedding hỏng là lỗi dịch vụ (503), còn lại do tệp (422).
        status = 503 if out.status == "EMBEDDING_FAILED" else 422
        return JSONResponse(status_code=status, content={
            "success": False, "total": 1, "message": out.message,
            "data": [out.model_dump()], "code": out.status,
        })
    return BaseResponse.ok([out], "Đã tạo bản nháp — xuất bản vẫn qua cổng đánh giá ở trang Kho tri thức.")


@router.get("/settings", response_model=BaseResponse[dict])
async def get_settings(
    actor: ConsoleActor = Depends(require_any_permission("ai:metrics:read", "ai:member:manage", "ai:audit:read")),
):
    data = await tools_service.get_runtime_settings(actor)
    return BaseResponse.ok([data], "OK")


@router.post("/settings/compute", response_model=BaseResponse[dict])
@router.put("/settings/compute", response_model=BaseResponse[dict])
async def update_compute_settings(
    payload: ComputeSettingsIn,
    actor: ConsoleActor = Depends(require_any_permission("ai:prompt:edit", "ai:model:evaluate")),
):
    data = await tools_service.update_compute_settings(actor, payload.model_dump(exclude_none=True))
    return BaseResponse.ok([data], "Đã cập nhật cấu hình phần cứng GPU/CPU & Engine.")


@router.post("/settings/policy", response_model=BaseResponse[dict])
@router.put("/settings/policy", response_model=BaseResponse[dict])
async def update_policy_settings(
    payload: PolicySettingsIn,
    actor: ConsoleActor = Depends(require_permission("ai:policy:threshold")),
):
    data = await tools_service.update_policy_settings(actor, payload.model_dump(exclude_none=True))
    return BaseResponse.ok([data], "Đã cập nhật ngưỡng AI & chính sách vận hành.")


@router.post("/engines/action", response_model=BaseResponse[dict])
async def engine_action(
    payload: EngineActionIn,
    actor: ConsoleActor = Depends(require_any_permission("ai:model:evaluate", "ai:prompt:edit")),
):
    data = await tools_service.engine_action(actor, payload.action)
    if payload.action == "warmup":
        msg = "Đã nạp sẵn model Vision vào bộ nhớ."
    elif payload.action in ("reload_llm", "restart_llm"):
        msg = "Đã nạp lại mô hình LLM (Hot Reload) thành công."
    else:
        msg = "Đã giải phóng model Vision khỏi RAM/VRAM."
    return BaseResponse.ok([data], msg)


@router.get("/sessions", response_model=BaseResponse[dict])
async def list_sessions(
    actor: ConsoleActor = Depends(require_any_permission("ai:metrics:read", "ai:member:manage", "ai:audit:read")),
):
    rows = await tools_service.list_sessions(actor)
    return BaseResponse.ok(rows, "OK")


@router.post("/sessions/{session_id}/revoke", response_model=BaseResponse[dict])
async def revoke_session(
    session_id: UUID,
    payload: RevokeSessionIn,
    actor: ConsoleActor = Depends(require_any_permission("ai:metrics:read", "ai:member:manage", "ai:audit:read")),
):
    res = await tools_service.revoke_session_by_id(actor, str(session_id), payload.reason or "")
    return BaseResponse.ok([res], "Đã thu hồi phiên đăng nhập.")
