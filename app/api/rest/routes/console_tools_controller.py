"""Công cụ thử trong AI Console — thay trang dev `/dashboard` cũ (IPLMS ADR-0050)."""
import json
import time
from typing import Any, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.rest.console_access import require_any_permission, require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.config import get_config
from app.core.console import ConsoleActor, console_tools_service
from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES
from app.core.copilot.dtos.copilot_dto import CopilotAnswer
from app.util.logger import logger

router = APIRouter(prefix="/tools", tags=["AI Console tools"])


class Check(BaseModel):
    key: str
    label: str
    ok: bool


class EngineStatus(BaseModel):
    # None = không biết chắc (UI hiện "—"), không có giá trị mặc định nào giả làm số đo.
    yolo_weights_path: str
    yolo_weights_bytes: Optional[int]
    yolo_version: str
    yolo_loaded: Optional[bool]
    ocr_languages: List[str]
    ocr_cache_dir: Optional[str]
    ocr_loaded: Optional[bool]
    onnx_enabled: bool
    torch_version: Optional[str]
    cuda_available: Optional[bool]


class SystemCheck(BaseModel):
    checks: List[Check]
    llm_model: str
    telemetry_enabled: bool
    vision_device: str
    telemetry_retention_days: int
    vision_retention_days: int
    engines: EngineStatus


class AnprTryOut(BaseModel):
    plate_number: str
    confidence: Optional[float]
    vehicle_type: Optional[str]
    plate_color: Optional[str]
    latency_ms: Optional[float]
    crop_image: Optional[str] = None
    crop_plate_image_url: Optional[str] = None


class ClipEventOut(BaseModel):
    plate_number: str
    confidence: float
    best_time_s: float
    start_time_s: float
    end_time_s: float
    frame_count: int
    crop_image: Optional[str] = None


class AnprClipOut(BaseModel):
    sampled_frames: int
    plate_reads: int
    latency_ms: float
    events: List[ClipEventOut]


class VerifyMatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_vehicle_type: str = Field(min_length=1, max_length=64)
    current_vehicle_type: str = Field(min_length=1, max_length=64)


class VerifyMatchOut(BaseModel):
    is_matched: bool
    similarity_score: Optional[float]
    mismatch_reason: str


class KnowledgeDocOut(BaseModel):
    id: str
    title: str
    category: str
    source: str
    chunk_count: int
    latest_version_no: int
    latest_status: str
    published_version_no: int
    updated_at: str


class DocumentChunkItem(BaseModel):
    ordinal: int
    section_title: str
    content: str


class DocumentVersionItem(BaseModel):
    version_no: int
    status: str
    chunk_count: int
    created_at: str
    published_at: str


class DocumentChunksOut(BaseModel):
    version_no: int
    status: str
    total: int
    chunks: List[DocumentChunkItem]
    versions: List[DocumentVersionItem]


# Hợp đồng body của Chat Studio (ai bug-017). Giữ khớp với
# ui/src/pages/Copilot/components/ChatStudio/askContract.ts (ASK_BODY_FIELDS);
# test/test_console_tools.py và ChatStudio.test.tsx đối chiếu danh sách này.
ASK_BODY_FIELDS = ("query", "parking_lot_id", "min_similarity", "top_k", "temperature", "history")


class DeleteDocOut(BaseModel):
    deleted: int
    document_id: str


class ChatMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern=r"^(user|assistant|system)$")
    content: str = Field(max_length=4000)


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    parking_lot_id: Optional[str] = Field(None, max_length=128)
    # Biên khớp thanh trượt Inspector. min_similarity chỉ làm truy xuất chặt hơn cấu hình
    # (rag_pipeline._limits), không nới được cổng NO_CONTEXT.
    min_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=1, le=10)
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    history: Optional[List[ChatMessageIn]] = Field(None, max_length=10)

    def tuning(self) -> dict:
        return {
            "top_k": self.top_k,
            "min_similarity": self.min_similarity,
            "temperature": self.temperature,
            "history": [h.model_dump() for h in self.history] if self.history else None,
        }


class IngestOut(BaseModel):
    document_id: str
    status: str
    ok: bool
    chunk_count: int
    duration_ms: float
    message: str
    version_id: str
    version_no: int


class ForecastSimulateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    area_id: str = Field(default="AREA_CENTRAL_01", min_length=1, max_length=128)
    day_of_week: int = Field(default=4, ge=0, le=6)
    total_capacity: int = Field(default=350, ge=10, le=10000)
    base_hourly_rate: float = Field(default=25000.0, ge=0.0)


@router.post("/forecast/simulate", response_model=BaseResponse[dict])
async def simulate_forecast(
    payload: ForecastSimulateIn,
    actor: ConsoleActor = Depends(require_permission("ai:metrics:read")),
):
    result = await console_tools_service.simulate_forecast(
        actor,
        area_id=payload.area_id,
        day_of_week=payload.day_of_week,
        total_capacity=payload.total_capacity,
        base_hourly_rate=payload.base_hourly_rate,
    )
    return BaseResponse.ok([result], "Đã chạy Pipeline 3: Lakehouse Parquet -> LightGBM/Prophet -> Dynamic Surge Tariff.")


@router.get("/system", response_model=BaseResponse[SystemCheck])
async def system(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
    return BaseResponse.ok([SystemCheck(**await console_tools_service.system_check(actor))], "OK")


@router.post("/anpr/recognize", response_model=BaseResponse[AnprTryOut])
async def try_anpr(
    file: UploadFile = File(...),
    lane_id: Optional[str] = Form(None, max_length=128),
    actor: ConsoleActor = Depends(require_permission("ai:model:evaluate")),
):
    image = await file.read(KNOWLEDGE_MAX_FILE_BYTES + 1)
    result = await console_tools_service.try_anpr(actor, image, lane_id)
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
    result = await console_tools_service.try_anpr_clip(actor, clip, file.content_type or "", mode == "motion")
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return BaseResponse.ok([AnprClipOut(**result)], "Kết quả đọc clip (clip không được lưu).")


@router.post("/vision/verify-match", response_model=BaseResponse[VerifyMatchOut])
async def verify_match(payload: VerifyMatchIn, actor: ConsoleActor = Depends(require_permission("ai:model:evaluate"))):
    result = await console_tools_service.verify_match(
        actor, payload.expected_vehicle_type, payload.current_vehicle_type
    )
    return BaseResponse.ok([VerifyMatchOut(**result)], "Đối chiếu theo loại xe; chưa so ảnh.")


@router.get("/knowledge/documents", response_model=BaseResponse[KnowledgeDocOut])
async def knowledge_documents(
    parking_lot_id: Optional[str] = Query(None, max_length=128),
    actor: ConsoleActor = Depends(require_permission("ai:prompt:edit")),
):
    docs = await console_tools_service.knowledge_documents(actor, parking_lot_id)
    return BaseResponse.ok([KnowledgeDocOut(**d) for d in docs], "OK")


@router.delete("/knowledge/documents/{document_id}", response_model=BaseResponse[DeleteDocOut])
async def delete_knowledge_document(
    document_id: str,
    parking_lot_id: Optional[str] = Query(None, max_length=128),
    actor: ConsoleActor = Depends(require_permission("ai:prompt:edit")),
):
    deleted_count = await console_tools_service.delete_knowledge_document(actor, document_id, parking_lot_id)
    return BaseResponse.ok([DeleteDocOut(deleted=deleted_count, document_id=document_id)], f"Đã xóa tài liệu {document_id}")


@router.get("/knowledge/documents/{document_id}/chunks", response_model=BaseResponse[DocumentChunksOut])
async def get_document_chunks(
    document_id: str,
    parking_lot_id: Optional[str] = Query(None, max_length=128),
    version_no: int = Query(0, ge=0),
    actor: ConsoleActor = Depends(require_permission("ai:prompt:edit")),
):
    chunks_data = await console_tools_service.document_chunks(actor, document_id, parking_lot_id, version_no)
    return BaseResponse.ok([DocumentChunksOut(**chunks_data)], "OK")


@router.post("/copilot/stream")
async def try_copilot_stream(payload: AskIn, actor: ConsoleActor = Depends(require_any_permission("ai:prompt:edit", "ai:chatlog:read"))):
    async def event_generator():
        try:
            async for chunk in console_tools_service.try_copilot_stream(
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
                "token": f"\n\n⚠️ Lỗi kết nối mô hình ngôn ngữ (LLM): {exc}",
                "is_finished": True,
                "sources": [],
                "citations": [],
                "confidence": 0.0,
                "refused": True,
                "guardrail_triggered": "connection_error",
                "prompt_version": "v1",
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
    answer = await console_tools_service.try_copilot(actor, payload.query, payload.parking_lot_id, **payload.tuning())
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
    result = await console_tools_service.ingest_draft(
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


class ComputeSettingsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    preset: Optional[str] = Field(None, max_length=32)
    vision_device: Optional[str] = Field(None, max_length=16)
    onnx_enabled: Optional[bool] = None
    vision_warmup_on_start: Optional[bool] = None
    local_llm_gpu_layers: Optional[int] = Field(None, ge=0, le=64)
    local_llm_ctx_size: Optional[int] = Field(None, ge=512, le=32768)
    local_llm_threads: Optional[int] = Field(None, ge=1, le=64)
    local_llm_parallel_slots: Optional[int] = Field(None, ge=1, le=8)

    @model_validator(mode="before")
    @classmethod
    def reject_model_fields(cls, data: Any) -> Any:
        # extra="ignore" sẽ nuốt im hai trường này và báo lưu thành công mà không có tác dụng
        # (REQ-020 X2); model theo tác vụ đổi bằng revision ở Models & Connections (ADR-0061 §2).
        if isinstance(data, dict) and ({"llm_provider", "llm_model"} & data.keys()):
            raise ValueError("Đổi provider/model ở trang Models & Connections, không ở Settings.")
        return data


class PolicySettingsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rag_min_similarity: Optional[float] = Field(None, ge=0.05, le=0.95)
    rag_top_k: Optional[int] = Field(None, ge=1, le=20)
    llm_timeout_seconds: Optional[float] = Field(None, ge=5.0, le=300.0)
    llm_max_output_tokens: Optional[int] = Field(None, ge=128, le=8192)
    vehicle_min_confidence: Optional[float] = Field(None, ge=0.1, le=0.99)
    default_lane_id: Optional[str] = Field(None, max_length=64)
    telemetry_enabled: Optional[bool] = None
    telemetry_retention_days: Optional[int] = Field(None, ge=1, le=365)
    vision_retention_days: Optional[int] = Field(None, ge=1, le=365)
    reason: str = Field(..., min_length=3, max_length=500)


class EngineActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(..., pattern="^(warmup|unload|reload_llm|restart_llm)$")


class RevokeSessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Optional[str] = Field("", max_length=200)


@router.get("/settings", response_model=BaseResponse[dict])
async def get_settings(
    actor: ConsoleActor = Depends(require_any_permission("ai:metrics:read", "ai:member:manage", "ai:audit:read")),
):
    data = await console_tools_service.get_runtime_settings(actor)
    return BaseResponse.ok([data], "OK")


@router.post("/settings/compute", response_model=BaseResponse[dict])
@router.put("/settings/compute", response_model=BaseResponse[dict])
async def update_compute_settings(
    payload: ComputeSettingsIn,
    actor: ConsoleActor = Depends(require_any_permission("ai:prompt:edit", "ai:model:evaluate")),
):
    data = await console_tools_service.update_compute_settings(actor, payload.model_dump(exclude_none=True))
    return BaseResponse.ok([data], "Đã cập nhật cấu hình phần cứng GPU/CPU & Engine.")


@router.post("/settings/policy", response_model=BaseResponse[dict])
@router.put("/settings/policy", response_model=BaseResponse[dict])
async def update_policy_settings(
    payload: PolicySettingsIn,
    actor: ConsoleActor = Depends(require_permission("ai:policy:threshold")),
):
    data = await console_tools_service.update_policy_settings(actor, payload.model_dump(exclude_none=True))
    return BaseResponse.ok([data], "Đã cập nhật ngưỡng AI & chính sách vận hành.")


@router.post("/engines/action", response_model=BaseResponse[dict])
async def engine_action(
    payload: EngineActionIn,
    actor: ConsoleActor = Depends(require_any_permission("ai:model:evaluate", "ai:prompt:edit")),
):
    data = await console_tools_service.engine_action(actor, payload.action)
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
    rows = await console_tools_service.list_sessions(actor)
    return BaseResponse.ok(rows, "OK")


@router.post("/sessions/{session_id}/revoke", response_model=BaseResponse[dict])
async def revoke_session(
    session_id: UUID,
    payload: RevokeSessionIn,
    actor: ConsoleActor = Depends(require_any_permission("ai:metrics:read", "ai:member:manage", "ai:audit:read")),
):
    res = await console_tools_service.revoke_session_by_id(actor, str(session_id), payload.reason or "")
    return BaseResponse.ok([res], "Đã thu hồi phiên đăng nhập.")
