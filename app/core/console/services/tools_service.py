"""Công cụ thử trong AI Console: kiểm cấu hình, hỏi thử Copilot, nạp bản nháp tri thức (IPLMS ADR-0050).

Chạy NGAY trong process console, gọi thẳng `app/core` — không đi qua REST/gRPC của
process inference (ADR-0048 §1). Không bao giờ trả giá trị secret/URL, chỉ "đã cấu
hình hay chưa".
"""
from __future__ import annotations

import asyncio
import importlib.metadata
import os
import sys
from typing import Any, Optional
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
# Ảnh thử ANPR trên console: cùng trần với tệp tri thức, đủ cho ảnh camera cổng.
ANPR_TRY_MAX_BYTES = KNOWLEDGE_MAX_FILE_BYTES
_ALLOWED_SUFFIXES = (".pdf", ".docx", ".txt", ".md", ".markdown")


def _lot(parking_lot_id: Optional[str]) -> Optional[str]:
    value = (parking_lot_id or "").strip()
    if len(value) > 128:
        raise ValueError("Mã bãi tối đa 128 ký tự.")
    return value or None


def _engine_status(vision) -> dict[str, Any]:
    """Trạng thái engine Vision đọc từ cấu hình, đĩa và bộ nhớ process — không nạp model.

    Trường nào không biết chắc thì None để UI hiện "—" (ai bug-018: không hằng số).
    """
    path = vision.yolo_model_path
    loaded_yolo = loaded_ocr = None
    try:
        from app.core.vision.engines.anpr import models as anpr_models

        loaded_yolo = anpr_models.yolo_model() is not None
        loaded_ocr = anpr_models.ocr_reader() is not None
    except Exception:  # noqa: BLE001 — thiếu thư viện vision thì báo "không rõ"
        pass
    cuda = False
    torch_version = None
    try:
        import torch
        torch_version = torch.__version__
        cuda = bool(torch.cuda.is_available())
    except Exception:
        try:
            torch_version = importlib.metadata.version("torch")
        except Exception:
            torch_version = None
        cuda = False
    return {
        "yolo_weights_path": path,
        "yolo_weights_bytes": os.path.getsize(path) if os.path.isfile(path) else None,
        "yolo_version": vision.yolo_model_version,
        "yolo_loaded": loaded_yolo,
        "ocr_languages": vision.ocr_language_list,
        "ocr_cache_dir": vision.ocr_model_storage_dir or None,
        "ocr_loaded": loaded_ocr,
        "onnx_enabled": vision.onnx_enabled,
        "torch_version": torch_version,
        "cuda_available": cuda,
    }


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
            "llm_model": getattr(cfg.llm, "active_model_name", cfg.llm.llm_model),
            "telemetry_enabled": cfg.telemetry.enabled,
            "vision_device": getattr(cfg.vision, "resolved_device", cfg.vision.device),
            "telemetry_retention_days": cfg.telemetry.retention_days,
            "vision_retention_days": cfg.console.vision_retention_days,
            "engines": _engine_status(cfg.vision),
        }

    async def try_anpr(self, actor: ConsoleActor, image: bytes, lane_id: Optional[str] = None) -> dict:
        """Chạy đúng engine ANPR đang nạp trong process này trên một ảnh (ai bug-018).

        Không lưu ảnh (persist_files=False): ảnh biển số là PII, lượt thử không để lại file.
        """
        access_policy.require(actor, "ai:model:evaluate")
        if not image:
            raise ValueError("Ảnh rỗng.")
        if len(image) > ANPR_TRY_MAX_BYTES:
            raise ValueError("Ảnh vượt 8 MB.")
        from app.core.vision.dtos.vision_dto import RecognizePlateCommand
        from app.core.vision.services.anpr_service import AnprService

        command = RecognizePlateCommand(image_data=image, lane_id=_lot(lane_id))
        result = await asyncio.to_thread(AnprService.recognize_bytes, command, False)

        crop_image_b64 = None
        crop_bytes = getattr(result, "crop_bytes", None)
        if crop_bytes:
            import base64
            crop_image_b64 = f"data:image/jpeg;base64,{base64.b64encode(crop_bytes).decode('ascii')}"

        return {
            "plate_number": result.plate_number,
            "confidence": result.confidence,
            "vehicle_type": result.vehicle_type,
            "plate_color": result.plate_color,
            "latency_ms": round(result.process_time * 1000, 1) if result.process_time is not None else None,
            "crop_image": crop_image_b64,
        }

    async def verify_match(self, actor: ConsoleActor, expected_type: str, current_type: str) -> dict:
        """Đối chiếu loại xe vào/ra bằng anti_fraud_service thật (ai bug-018).

        Service chưa so ảnh (SUGGESTION-007 B6) nên `similarity_score` luôn là None ở đây,
        không trả hằng số 0.0 của service như thể đó là số đo.
        """
        access_policy.require(actor, "ai:model:evaluate")
        from app.core.constants import SIMILARITY_NOT_MEASURED
        from app.core.vision.dtos.vision_dto import VehicleMatchQuery
        from app.core.vision.services.anti_fraud_service import anti_fraud_service

        result = anti_fraud_service.verify_vehicle_match(VehicleMatchQuery(
            checkin_crop_url="", checkout_crop_url="",
            expected_vehicle_type=expected_type.strip(), current_vehicle_type=current_type.strip(),
        ))
        reason = getattr(result.mismatch_reason, "value", result.mismatch_reason)
        measured = result.similarity_score != SIMILARITY_NOT_MEASURED
        return {
            "is_matched": result.is_matched,
            "similarity_score": result.similarity_score if measured else None,
            "mismatch_reason": str(reason or ""),
        }

    async def knowledge_documents(self, actor: ConsoleActor, parking_lot_id: Optional[str] = None) -> list[dict]:
        """Tài liệu thật trong kho tri thức (metadata, không kèm nội dung) — ai bug-018."""
        access_policy.require(actor, "ai:prompt:edit")
        docs = await self._ingestion_service().list(_lot(parking_lot_id))
        return [
            {
                "id": d.document_id,
                "title": d.file_name,
                "category": d.category,
                "source": d.file_name,
                "chunk_count": d.chunk_count,
                "latest_version_no": d.latest_version_no,
                "latest_status": d.latest_status,
                "published_version_no": d.published_version_no,
                "updated_at": d.updated_at,
            }
            for d in docs
        ]

    async def delete_knowledge_document(
        self, actor: ConsoleActor, document_id: str, parking_lot_id: Optional[str] = None
    ) -> int:
        access_policy.require(actor, "ai:prompt:edit")
        deleted = await self._ingestion_service().delete(document_id, _lot(parking_lot_id))
        await self.store.add_audit(
            actor.member_id, "knowledge.delete", "knowledge_document",
            str(document_id), f"Đã xóa tài liệu {document_id}",
        )
        return deleted

    async def try_copilot_stream(
        self, actor: ConsoleActor, query: str, parking_lot_id: Optional[str] = None,
        top_k: Optional[int] = None, min_similarity: Optional[float] = None,
        temperature: Optional[float] = None,
    ):
        # Tham số thử chỉ dùng được với quyền sửa prompt, cùng quyền của cả lượt thử.
        access_policy.require(actor, "ai:prompt:edit")
        query = (query or "").strip()
        if not 1 <= len(query) <= 2000:
            raise ValueError("Câu hỏi cần 1–2000 ký tự.")
        request = AskQuestionRequest(
            query=query, user_id=actor.member_id, user_role="console",
            parking_lot_id=_lot(parking_lot_id), preview=True,
            top_k=top_k, min_similarity=min_similarity, temperature=temperature,
        )
        async for chunk in self.copilot.stream_answer(request):
            yield chunk

    async def try_copilot(
        self, actor: ConsoleActor, query: str, parking_lot_id: Optional[str] = None,
        top_k: Optional[int] = None, min_similarity: Optional[float] = None,
        temperature: Optional[float] = None,
    ) -> CopilotAnswer:
        access_policy.require(actor, "ai:prompt:edit")
        query = (query or "").strip()
        if not 1 <= len(query) <= 2000:
            raise ValueError("Câu hỏi cần 1–2000 ký tự.")
        request = AskQuestionRequest(
            query=query, user_id=actor.member_id, user_role="console",
            parking_lot_id=_lot(parking_lot_id), preview=True,
            top_k=top_k, min_similarity=min_similarity, temperature=temperature,
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
