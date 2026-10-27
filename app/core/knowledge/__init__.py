"""Domain Knowledge — nạp quy chế bãi xe (PDF/DOCX/TXT/MD) vào pgvector cho RAG (Pipeline 2)."""
from app.core.knowledge.dtos.knowledge_dto import (
    IngestDocumentCommand,
    IngestResult,
    KnowledgeChunk,
    KnowledgeDocumentItem,
    KnowledgeDocumentSummary,
    TextChunk,
)
from app.core.knowledge.guardrails.injection_scan import find_instructions
from app.core.knowledge.services.ingestion_service import IngestionService, ingestion_service

__all__ = [
    "find_instructions",
    "IngestDocumentCommand",
    "IngestResult",
    "IngestionService",
    "KnowledgeChunk",
    "KnowledgeDocumentItem",
    "KnowledgeDocumentSummary",
    "TextChunk",
    "ingestion_service",
]
