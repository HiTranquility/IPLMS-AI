"""Document ingestion orchestration: parse → chunk → embed → transaction."""
from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from app.core.constants import DOCUMENT_PARSE_TIMEOUT_SECONDS
from app.core.enums import IngestStatus
from app.core.exceptions import (
    DocumentTooLargeError,
    EmbeddingError,
    NoTextLayerError,
    UnsupportedFormatError,
)
from app.core.knowledge.dtos.knowledge_dto import (
    IngestDocumentCommand,
    IngestResult,
    KnowledgeDocumentSummary,
)
from app.core.knowledge.engines.chunker import chunk_text
from app.core.knowledge.engines.document_parser import parse_document
from app.infra.database.pgvector_client import pgvector_client
from app.infra.embedding import embedding_client
from app.util.logger import logger


class IngestionService:
    def __init__(self, embedder=None, vector_store=None) -> None:
        self.embedder = embedder or embedding_client
        self.vector_store = vector_store or pgvector_client

    async def ingest(self, command: IngestDocumentCommand) -> IngestResult:
        started = time.perf_counter()
        document_id = str(command.document_id or uuid4())

        try:
            parsed = await asyncio.wait_for(
                asyncio.to_thread(parse_document, command.file_data, command.file_name),
                timeout=DOCUMENT_PARSE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return self._result(
                document_id,
                IngestStatus.FILE_TOO_LARGE,
                started,
                "Tài liệu mất quá nhiều thời gian để phân tích.",
            )
        except DocumentTooLargeError as exc:
            return self._result(document_id, IngestStatus.FILE_TOO_LARGE, started, str(exc))
        except NoTextLayerError as exc:
            return self._result(document_id, IngestStatus.NO_TEXT_LAYER, started, str(exc))
        except UnsupportedFormatError as exc:
            return self._result(document_id, IngestStatus.UNSUPPORTED_FORMAT, started, str(exc))

        text_chunks = chunk_text(parsed.text)
        if not text_chunks:
            return self._result(
                document_id,
                IngestStatus.NO_TEXT_LAYER,
                started,
                "Tài liệu không tạo được đoạn tri thức có nội dung.",
            )

        try:
            vectors = await self.embedder.embed_texts([chunk.content for chunk in text_chunks])
        except EmbeddingError as exc:
            logger.warning("Knowledge embedding failed document=%s: %s", document_id, exc)
            return self._result(
                document_id,
                IngestStatus.EMBEDDING_FAILED,
                started,
                str(exc),
            )

        chunks = [
            {
                "content": chunk.content,
                "embedding": vector,
                "ordinal": chunk.ordinal,
                "section_title": chunk.section_title,
                "metadata": {
                    "document_format": parsed.doc_format.value,
                    "page_count": parsed.page_count,
                    "warnings": parsed.warnings,
                },
            }
            for chunk, vector in zip(text_chunks, vectors, strict=True)
        ]
        version = await self.vector_store.save_draft_version(
            document_id=document_id,
            file_name=command.file_name,
            category=command.category,
            parking_lot_id=command.parking_lot_id,
            uploaded_by=command.uploaded_by,
            chunks=chunks,
        )
        return IngestResult(
            document_id=document_id,
            status=IngestStatus.SUCCESS,
            chunk_count=len(chunks),
            message="Đã nạp bản nháp — chạy test rồi xuất bản để khách thấy.",
            process_time=time.perf_counter() - started,
            version_id=version["version_id"],
            version_no=version["version_no"],
        )

    async def delete(
        self, document_id: str, parking_lot_id: str | None, draft_only: bool = False
    ) -> int:
        return await self.vector_store.delete_document(document_id, parking_lot_id, draft_only)

    async def list(self, parking_lot_id: str | None) -> list[KnowledgeDocumentSummary]:
        rows = await self.vector_store.list_documents(parking_lot_id)
        return [KnowledgeDocumentSummary(**row) for row in rows]

    @staticmethod
    def _result(
        document_id: str,
        status: IngestStatus,
        started: float,
        message: str,
    ) -> IngestResult:
        return IngestResult(
            document_id=document_id,
            status=status,
            chunk_count=0,
            message=message,
            process_time=time.perf_counter() - started,
        )


ingestion_service = IngestionService()
