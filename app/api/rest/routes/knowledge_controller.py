"""REST route cho Knowledge Ingestion & Management."""
import json
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.api.rest.schemas.base_response import BaseResponse
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand, IngestResult
from app.core.knowledge.services import ingestion_service
from app.infra.database.pgvector_client import pgvector_client

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

def get_seed_path() -> str:
    candidates = [
        os.path.join(os.getcwd(), "data", "knowledge", "regulations_seed.json"),
        os.path.join("/app", "data", "knowledge", "regulations_seed.json"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/knowledge/regulations_seed.json")),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


class IngestResponse(BaseModel):
    document_id: str
    status: str
    chunk_count: int
    duration_ms: float
    message: str


@router.get("/seeds")
async def get_seed_regulations() -> Dict[str, Any]:
    """Lấy danh sách các tài liệu quy chế mẫu có sẵn trong repository."""
    seed_path = get_seed_path()
    if not os.path.exists(seed_path):
        return {"total": 0, "items": []}
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        return {"total": len(items), "items": items}
    except Exception as exc:
        return {"total": 0, "error": str(exc), "items": []}


@router.get("/stats")
async def get_knowledge_stats() -> Dict[str, Any]:
    """Kiểm tra thống kê các tài liệu và chunk đã nạp trong pgvector."""
    try:
        stats = await pgvector_client.get_knowledge_stats()
        return {"status": "connected", "pgvector": stats}
    except Exception as exc:
        # Fallback to local files if pgvector is offline
        seed_count = 0
        seed_path = get_seed_path()
        if os.path.exists(seed_path):
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    seed_count = len(json.load(f))
            except Exception:
                pass
        return {
            "status": "offline_fallback",
            "message": str(exc),
            "pgvector": {"documents": 0, "chunks": 0, "global_chunks": 0},
            "local_seed_documents": seed_count,
        }


@router.post("/ingest", response_model=BaseResponse[IngestResponse])
async def ingest_document(
    file: UploadFile = File(...),
    category: str = Form("regulation"),
    parking_lot_id: Optional[str] = Form(None),
) -> BaseResponse[IngestResponse]:
    """Nạp tài liệu PDF hoặc DOCX vào kho tri thức."""
    try:
        content = await file.read()
        cmd = IngestDocumentCommand(
            file_name=file.filename or "unknown.pdf",
            file_data=content,
            category=category,
            parking_lot_id=parking_lot_id or None,
            document_id=uuid4(),
            uploaded_by="ui_operator",
        )
        res: IngestResult = await ingestion_service.ingest(cmd)
        item = IngestResponse(
            document_id=str(res.document_id),
            status=res.status.value if hasattr(res.status, "value") else str(res.status),
            chunk_count=res.chunk_count,
            duration_ms=res.duration_ms,
            message=res.message,
        )
        msg = "Ingestion completed" if item.status == "SUCCESS" else f"Ingestion warning: {item.message}"
        return BaseResponse.ok([item], msg)
    except Exception as exc:
        return BaseResponse.fail(f"Failed to ingest: {exc}")
