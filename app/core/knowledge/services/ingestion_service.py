"""Document ingestion orchestration: parse → chunk → embed → transaction."""
from __future__ import annotations

import asyncio
import hashlib
import time
from collections import defaultdict, deque
from uuid import uuid4

from app.core.knowledge.constants import DOCUMENT_PARSE_TIMEOUT_SECONDS
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
from app.core.knowledge.guardrails.injection_scan import find_injection_phrases
from app.infra.database.pgvector_client import pgvector_client
from app.infra.embedding import embedding_client
from app.util.logger import logger


def _injection_flags(content: str) -> dict:
    # Cổng xuất bản đọc khoá này (PROB-046 phase 2); đoạn sạch thì không có khoá.
    flags = find_injection_phrases(content)
    return {"injection_flags": flags} if flags else {}


def _ingest_message(flagged: list[str]) -> str:
    # UI ghép sau câu "Đã nạp <file> thành bản nháp vN (M đoạn)." nên không lặp lại ý đó.
    if not flagged:
        return "Chạy test rồi xuất bản để khách thấy."
    return (
        f"Lưu ý: có {len(flagged)} chỗ giống lệnh gửi cho trợ lý AI "
        f"(vd “{flagged[0]}”). Bản này sẽ không xuất bản được cho tới khi bạn xoá "
        "những chỗ đó và nạp lại."
    )


class IngestionService:
    _SCOPE_WINDOW_SECONDS = 60.0
    _MAX_INGESTS_PER_WINDOW = 15

    def __init__(self, embedder=None, vector_store=None) -> None:
        self.embedder = embedder or embedding_client
        self.vector_store = vector_store or pgvector_client
        self._scope_buckets: dict[str, deque[float]] = defaultdict(deque)

    def _check_scope_rate_limit(self, scope_key: str) -> bool:
        now = time.monotonic()
        bucket = self._scope_buckets[scope_key]
        while bucket and now - bucket[0] > self._SCOPE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= self._MAX_INGESTS_PER_WINDOW:
            return False
        bucket.append(now)
        return True

    async def ingest(self, command: IngestDocumentCommand) -> IngestResult:
        started = time.perf_counter()
        document_id = str(command.document_id or uuid4())
        scope_key = str(command.parking_lot_id or "global")
        if not self._check_scope_rate_limit(scope_key):
            return self._result(
                document_id,
                IngestStatus.FILE_TOO_LARGE,
                started,
                "Tốc độ nạp tài liệu vượt ngưỡng an toàn (chống DDoS). Vui lòng đợi ít giây rồi thử lại.",
            )
        file_sha256 = hashlib.sha256(command.file_data).hexdigest()

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
                    "file_sha256": file_sha256,
                    **_injection_flags(chunk.content),
                },
            }
            for chunk, vector in zip(text_chunks, vectors, strict=True)
        ]
        flagged = [s for c in chunks for s in c["metadata"].get("injection_flags", [])]
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
            message=_ingest_message(flagged),
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

    async def list_chunks(self, document_id: str, parking_lot_id: str | None,
                          version_no: int = 0) -> dict:
        return await self.vector_store.list_document_chunks(document_id, parking_lot_id, version_no)

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
