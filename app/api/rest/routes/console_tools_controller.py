import json
"""Công cụ thử trong AI Console — thay trang dev `/dashboard` cũ (IPLMS ADR-0050)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.rest.console_access import require_any_permission, require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.core.console.dtos import ConsoleActor
from app.core.console.services.tools_service import console_tools_service
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
ASK_BODY_FIELDS = ("query", "parking_lot_id", "min_similarity", "top_k", "temperature")


class DeleteDocOut(BaseModel):
    deleted: int
    document_id: str


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    parking_lot_id: Optional[str] = Field(None, max_length=128)
    # Biên khớp thanh trượt Inspector. min_similarity chỉ làm truy xuất chặt hơn cấu hình
    # (rag_pipeline._limits), không nới được cổng NO_CONTEXT.
    min_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=1, le=10)
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)

    def tuning(self) -> dict:
        return {"top_k": self.top_k, "min_similarity": self.min_similarity, "temperature": self.temperature}


class IngestOut(BaseModel):
    document_id: str
    status: str
    ok: bool
    chunk_count: int
    duration_ms: float
    message: str
    version_id: str
    version_no: int


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
