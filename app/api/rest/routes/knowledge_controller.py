"""Local-only knowledge ingestion through the existing draft/publication service."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel
from app.api.rest.developer_access import limit_developer_calls
from app.api.rest.schemas.base_response import BaseResponse
from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES
from app.core.enums import IngestStatus
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand
from app.core.knowledge.services.ingestion_service import ingestion_service

router = APIRouter(prefix="/knowledge", tags=["Developer knowledge"],
                   dependencies=[Depends(limit_developer_calls)])


class IngestResponse(BaseModel):
    document_id: str
    status: str
    chunk_count: int
    duration_ms: float
    message: str
    version_id: str
    version_no: int


@router.post("/ingest", response_model=BaseResponse[IngestResponse])
async def ingest_document(
    response: Response,
    file: UploadFile = File(...),
    document_id: UUID = Form(...),
    category: str = Form("regulation", max_length=128),
    parking_lot_id: Optional[str] = Form(None, max_length=128),
) -> BaseResponse[IngestResponse]:
    # Caller retains the document ID when retrying; never silently create a new document.
    content = await file.read(KNOWLEDGE_MAX_FILE_BYTES + 1)
    if len(content) > KNOWLEDGE_MAX_FILE_BYTES:
        raise HTTPException(413, "Document exceeds upload size limit")
    result = await ingestion_service.ingest(IngestDocumentCommand(
        file_name=file.filename or "unknown", file_data=content,
        category=category, parking_lot_id=parking_lot_id or None,
        document_id=document_id, uploaded_by="local-developer",
    ))
    item = IngestResponse(
        document_id=str(result.document_id), status=result.status.value,
        chunk_count=result.chunk_count, duration_ms=result.process_time * 1000,
        message=result.message, version_id=result.version_id, version_no=result.version_no,
    )
    success = result.status == IngestStatus.SUCCESS
    if not success:
        response.status_code = 503 if result.status == IngestStatus.EMBEDDING_FAILED else 422
    return BaseResponse(success=success, total=1, data=[item],
                        message="Draft ingested; publication requires evaluation" if success else result.message)
