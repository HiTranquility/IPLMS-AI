"""Công cụ thử trong AI Console: kiểm cấu hình, hỏi thử Copilot, nạp bản nháp tri thức (IPLMS ADR-0050).

Chạy NGAY trong process console, gọi thẳng `app/core` — không đi qua REST/gRPC của
process inference (ADR-0048 §1). Không bao giờ trả giá trị secret/URL, chỉ "đã cấu
hình hay chưa".
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.config import get_config
from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.core.constants import KNOWLEDGE_MAX_FILE_BYTES
from app.core.copilot.dtos.copilot_dto import AskQuestionRequest, CopilotAnswer
from app.core.copilot.services.copilot_service import copilot_service
from app.core.enums import IngestStatus
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand
from app.infra.database.console_store import console_store

CONSOLE_TRY_TASK = "console_try"
_ALLOWED_SUFFIXES = (".pdf", ".docx", ".txt", ".md", ".markdown")


def _lot(parking_lot_id: Optional[str]) -> Optional[str]:
    value = (parking_lot_id or "").strip()
    if len(value) > 128:
        raise ValueError("Mã bãi tối đa 128 ký tự.")
    return value or None


class ConsoleToolsService:
    def __init__(self, store=None, copilot=None, ingestion=None) -> None:
        self.store = store or console_store
        self.copilot = copilot or copilot_service
        self._ingestion = ingestion

    def _ingestion_service(self):
        # Nạp trễ: parser PDF/DOCX + client embedding chỉ cần khi có người nạp.
        if self._ingestion is None:
            from app.core.knowledge.services.ingestion_service import ingestion_service

            self._ingestion = ingestion_service
        return self._ingestion

    async def system_check(self, actor: ConsoleActor) -> dict:
        access_policy.require(actor, "ai:metrics:read")
        cfg = get_config()
        checks = [
            ("ai_database", "AI_DATABASE_URL (tri thức + telemetry)", bool(cfg.llm.database_url)),
            ("llm_key", "Khoá nhà cung cấp LLM", bool(cfg.llm.llm_api_key)),
            ("telemetry_hmac", "Khoá HMAC telemetry", bool(cfg.telemetry.hmac_key)),
            ("telemetry_price", "Giá token để tính chi phí",
             cfg.telemetry.price_input_per_mtok is not None and cfg.telemetry.price_output_per_mtok is not None),
            ("console_database", "AI_CONSOLE_DATABASE_URL", bool(cfg.console.database_url)),
            ("google_oidc", "Google OAuth client", bool(cfg.console.google_client_id and cfg.console.google_client_secret)),
            ("totp_key", "Khoá mã hoá TOTP", bool(cfg.console.totp_encryption_key)),
            ("cookie_secure", "Cookie chỉ qua HTTPS", cfg.console.cookie_secure),
        ]
        return {
            "checks": [{"key": k, "label": label, "ok": bool(ok)} for k, label, ok in checks],
            "llm_model": cfg.llm.llm_model,
            "telemetry_enabled": cfg.telemetry.enabled,
            "vision_device": cfg.vision.device,
            "telemetry_retention_days": cfg.telemetry.retention_days,
            "vision_retention_days": cfg.console.vision_retention_days,
        }

    async def try_copilot_stream(
        self, actor: ConsoleActor, query: str, parking_lot_id: Optional[str] = None
    ):
        access_policy.require(actor, "ai:prompt:edit")
        query = (query or "").strip()
        if not 1 <= len(query) <= 2000:
            raise ValueError("Câu hỏi cần 1–2000 ký tự.")
        request = AskQuestionRequest(
            query=query, user_id=actor.member_id, user_role="console",
            parking_lot_id=_lot(parking_lot_id), preview=False,
        )
        async for chunk in self.copilot.stream_answer(request):
            yield chunk

    async def try_copilot(
        self, actor: ConsoleActor, query: str, parking_lot_id: Optional[str] = None
    ) -> CopilotAnswer:
        access_policy.require(actor, "ai:prompt:edit")
        query = (query or "").strip()
        if not 1 <= len(query) <= 2000:
            raise ValueError("Câu hỏi cần 1–2000 ký tự.")
        request = AskQuestionRequest(
            query=query, user_id=actor.member_id, user_role="console",
            parking_lot_id=_lot(parking_lot_id), preview=False,
        )
        return await self.copilot.ask_question(request, task=CONSOLE_TRY_TASK)

    async def ingest_draft(
        self, actor: ConsoleActor, document_id: str, file_name: str, data: bytes,
        category: str = "regulation", parking_lot_id: Optional[str] = None,
    ) -> dict:
        access_policy.require(actor, "ai:prompt:edit")
        try:
            doc_uuid = UUID(document_id)
        except (ValueError, TypeError):
            raise ValueError("Mã tài liệu phải là UUID (giữ nguyên khi thử lại).") from None
        name = (file_name or "").strip()
        if not name.lower().endswith(_ALLOWED_SUFFIXES):
            raise ValueError("Chỉ nhận PDF, DOCX, TXT hoặc MD.")
        if not data:
            raise ValueError("Tệp rỗng.")
        if len(data) > KNOWLEDGE_MAX_FILE_BYTES:
            raise ValueError("Tệp vượt 8 MB.")
        category = (category or "regulation").strip()[:128] or "regulation"
        result = await self._ingestion_service().ingest(IngestDocumentCommand(
            file_name=name, file_data=data, category=category,
            parking_lot_id=_lot(parking_lot_id), document_id=doc_uuid, uploaded_by=actor.member_id,
        ))
        await self.store.add_audit(
            actor.member_id, f"knowledge.ingest_draft:{result.status.value}", "knowledge_document",
            str(result.document_id), f"{name} → bản nháp v{result.version_no}",
        )
        return {
            "document_id": str(result.document_id),
            "status": result.status.value,
            "ok": result.status == IngestStatus.SUCCESS,
            "chunk_count": result.chunk_count,
            "duration_ms": round(result.process_time * 1000, 1),
            "message": result.message,
            "version_id": result.version_id,
            "version_no": result.version_no,
        }


console_tools_service = ConsoleToolsService()
