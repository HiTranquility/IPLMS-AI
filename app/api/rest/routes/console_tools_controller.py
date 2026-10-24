import json
"""Công cụ thử trong AI Console — thay trang dev `/dashboard` cũ (IPLMS ADR-0050)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.rest.console_access import require_any_permission, require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.core.console.dtos import ConsoleActor
from app.core.console.services.tools_service import console_tools_service
from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES
from app.core.copilot.dtos.copilot_dto import CopilotAnswer

router = APIRouter(prefix="/tools", tags=["AI Console tools"])


class Check(BaseModel):
    key: str
    label: str
    ok: bool


class SystemCheck(BaseModel):
    checks: List[Check]
    llm_model: str
    telemetry_enabled: bool
    vision_device: str
    telemetry_retention_days: int
    vision_retention_days: int


# Hợp đồng body của Chat Studio (ai bug-017). Giữ khớp với
# ui/src/pages/Copilot/components/ChatStudio/askContract.ts (ASK_BODY_FIELDS);
# test/test_console_tools.py và ChatStudio.test.tsx đối chiếu danh sách này.
ASK_BODY_FIELDS = ("query", "parking_lot_id", "min_similarity", "top_k", "temperature")


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


@router.post("/copilot/stream")
async def try_copilot_stream(payload: AskIn, actor: ConsoleActor = Depends(require_any_permission("ai:prompt:edit", "ai:chatlog:read"))):
    async def event_generator():
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
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
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
