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
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand, IngestResult
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
            try:
                self._save_to_local_seed(command, text_chunks)
                return IngestResult(
                    document_id=document_id,
                    status=IngestStatus.SUCCESS,
                    chunk_count=len(text_chunks),
                    message="Đã nạp vào kho tri thức cục bộ (Local Knowledge Seed).",
                    process_time=time.perf_counter() - started,
                )
            except Exception as seed_exc:
                logger.warning("Failed to save to local seed: %s", seed_exc)

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
        await self.vector_store.replace_document(
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
            message="Đã nạp tài liệu vào kho tri thức.",
            process_time=time.perf_counter() - started,
        )

    async def delete(self, document_id: str, parking_lot_id: str | None) -> int:
        return await self.vector_store.delete_document(document_id, parking_lot_id)

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

    @staticmethod
    def _save_to_local_seed(command: IngestDocumentCommand, text_chunks: list[TextChunk]) -> None:
        import json
        import os
        candidates = [
            os.path.join(os.getcwd(), "data", "knowledge", "regulations_seed.json"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/knowledge/regulations_seed.json")),
        ]
        seed_path = next((c for c in candidates if os.path.exists(c)), candidates[0])
        existing = []
        if os.path.exists(seed_path):
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        existing = [item for item in existing if item.get("source") != command.file_name]

        for idx, chunk in enumerate(text_chunks, 1):
            title = chunk.section_title or f"{command.file_name} (Đoạn {idx})"
            existing.append({
                "category": command.category or "regulation",
                "title": title,
                "content": chunk.content,
                "source": command.file_name,
                "parking_lot_id": command.parking_lot_id,
            })

        os.makedirs(os.path.dirname(seed_path), exist_ok=True)
        with open(seed_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)


ingestion_service = IngestionService()
