"""Công cụ thử trong AI Console (IPLMS ADR-0050): quyền, không lộ secret, lượt thử tách khỏi số sản phẩm."""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.core.console.dtos import ConsoleActor
from app.core.console.services.tools_service import CONSOLE_TRY_TASK, ConsoleToolsService
from app.core.enums import IngestStatus
from app.core.exceptions import ConsoleAccessDenied

ML = ConsoleActor("m-ml", frozenset({"ai_ml_engineer"}))
ANALYST = ConsoleActor("m-an", frozenset({"ai_analyst"}))
DOC = "3f1c2a64-5b7d-4e8f-9a01-23456789abcd"


def service():
    copilot = AsyncMock()
    ingestion = AsyncMock()
    ingestion.ingest.return_value = SimpleNamespace(
        document_id=DOC, status=IngestStatus.SUCCESS, chunk_count=3, process_time=0.25,
        message="ok", version_id="v-1", version_no=2,
    )
    store = AsyncMock()
    return ConsoleToolsService(store=store, copilot=copilot, ingestion=ingestion), copilot, ingestion, store


class ConsoleToolsTest(unittest.IsolatedAsyncioTestCase):
    async def test_kiem_cau_hinh_khong_tra_gia_tri_secret(self):
        svc, *_ = service()
        secrets = {
            "AI_LLM_API_KEY": "sk-should-not-leak", "AI_CONSOLE_GOOGLE_CLIENT_SECRET": "gsecret-should-not-leak",
            "AI_DATABASE_URL": "postgresql://u:pw-should-not-leak@h/db",
        }
        from app.config import get_config

        get_config.cache_clear()
        try:
            with patch.dict(os.environ, secrets):
                report = await svc.system_check(ANALYST)
                self.assertTrue(next(c for c in report["checks"] if c["key"] == "llm_key")["ok"])
        finally:
            get_config.cache_clear()  # không để config có secret giả lọt sang test khác
        flat = repr(report)
        self.assertNotIn("should-not-leak", flat)
        self.assertTrue(all(isinstance(c["ok"], bool) for c in report["checks"]))

    async def test_hoi_thu_can_prompt_edit_va_ghi_task_rieng(self):
        svc, copilot, *_ = service()
        with self.assertRaises(ConsoleAccessDenied):
            await svc.try_copilot(ANALYST, "phí gửi xe?")
        await svc.try_copilot(ML, "  phí gửi xe?  ", " lot-1 ")
        request = copilot.ask_question.await_args.args[0]
        self.assertEqual(("phí gửi xe?", "console", "m-ml", "lot-1"),
                         (request.query, request.user_role, request.user_id, request.parking_lot_id))
        self.assertEqual(CONSOLE_TRY_TASK, copilot.ask_question.await_args.kwargs["task"])
        with self.assertRaises(ValueError):
            await svc.try_copilot(ML, "x" * 2001)

    async def test_nap_ban_nhap_kiem_dau_vao_va_ghi_audit(self):
        svc, _, ingestion, store = service()
        with self.assertRaisesRegex(ValueError, "UUID"):
            await svc.ingest_draft(ML, "abc", "quy-che.pdf", b"%PDF")
        with self.assertRaisesRegex(ValueError, "PDF, DOCX"):
            await svc.ingest_draft(ML, DOC, "anh.exe", b"MZ")
        with self.assertRaisesRegex(ValueError, "rỗng"):
            await svc.ingest_draft(ML, DOC, "quy-che.md", b"")
        result = await svc.ingest_draft(ML, DOC, "quy-che.md", b"# Quy che", parking_lot_id="")
        self.assertEqual((True, 3, 2), (result["ok"], result["chunk_count"], result["version_no"]))
        command = ingestion.ingest.await_args.args[0]
        self.assertEqual(("m-ml", None), (command.uploaded_by, command.parking_lot_id))
        self.assertEqual("knowledge.ingest_draft:SUCCESS", store.add_audit.await_args.args[1])


class StudioRealApiTest(unittest.IsolatedAsyncioTestCase):
    """bug-018: các studio gọi service thật trong process console, không hằng số."""

    async def test_anpr_thu_goi_engine_that_khong_luu_anh(self):
        svc, *_ = service()
        fake = SimpleNamespace(plate_number="51A12345", confidence=0.71, vehicle_type=None,
                               plate_color="white", process_time=0.123)
        with patch("app.core.vision.services.anpr_service.AnprService.recognize_bytes", return_value=fake) as run:
            out = await svc.try_anpr(ML, b"jpeg-bytes")
        self.assertFalse(run.call_args.args[1])  # persist_files=False
        self.assertEqual({"plate_number": "51A12345", "confidence": 0.71, "vehicle_type": None,
                          "plate_color": "white", "latency_ms": 123.0}, out)

    async def test_anpr_thu_can_quyen_va_anh_hop_le(self):
        svc, *_ = service()
        with self.assertRaises(ConsoleAccessDenied):
            await svc.try_anpr(ANALYST, b"x")
        with self.assertRaises(ValueError):
            await svc.try_anpr(ML, b"")

    async def test_doi_chieu_xe_khong_tra_diem_chua_do(self):
        svc, *_ = service()
        same = await svc.verify_match(ML, "car_sedan", "car_sedan")
        self.assertEqual({"is_matched": True, "similarity_score": None, "mismatch_reason": "OK"}, same)
        diff = await svc.verify_match(ML, "car_sedan", "motorbike")
        self.assertFalse(diff["is_matched"])
        self.assertEqual("VEHICLE_TYPE_MISMATCH", diff["mismatch_reason"])
        self.assertIsNone(diff["similarity_score"])

    async def test_danh_sach_tai_lieu_tri_thuc_that(self):
        svc, _, ingestion, _ = service()
        ingestion.list.return_value = [SimpleNamespace(
            document_id=DOC, file_name="bang-gia.pdf", category="tariff", chunk_count=4,
            latest_version_no=2, latest_status="DRAFT", published_version_no=1, updated_at="2026-10-24T00:00:00",
        )]
        docs = await svc.knowledge_documents(ML, " lot-1 ")
        ingestion.list.assert_awaited_once_with("lot-1")
        self.assertEqual("bang-gia.pdf", docs[0]["title"])
        self.assertEqual(4, docs[0]["chunk_count"])
        with self.assertRaises(ConsoleAccessDenied):
            await svc.knowledge_documents(ANALYST)

    async def test_trang_thai_engine_khong_bia_khi_thieu_weights(self):
        svc, *_ = service()
        with patch.dict(os.environ, {"AI_YOLO_MODEL_PATH": "/khong/ton/tai.pt"}):
            from app.config import get_config

            get_config.cache_clear()
            try:
                engines = (await svc.system_check(ML))["engines"]
            finally:
                get_config.cache_clear()
        self.assertEqual("/khong/ton/tai.pt", engines["yolo_weights_path"])
        self.assertIsNone(engines["yolo_weights_bytes"])
        self.assertIn(engines["yolo_loaded"], (None, False))


class ChatStudioContractTest(unittest.IsolatedAsyncioTestCase):
    """ai bug-017: body Chat Studio gửi phải qua được AskIn và tham số phải tới pipeline."""

    # Giữ khớp ui/src/pages/Copilot/components/ChatStudio/askContract.ts (ASK_BODY_FIELDS).
    UI_FIELDS = ("query", "parking_lot_id", "min_similarity", "top_k", "temperature")
    BODY = {"query": "phí gửi xe?", "parking_lot_id": "", "min_similarity": 0.72, "top_k": 4, "temperature": 0.1}

    def test_askin_nhan_dung_body_cua_chat_studio(self):
        from app.api.rest.routes.console_tools_controller import ASK_BODY_FIELDS, AskIn

        self.assertEqual(set(self.UI_FIELDS), set(ASK_BODY_FIELDS))
        self.assertEqual(set(ASK_BODY_FIELDS), set(AskIn.model_fields))
        payload = AskIn.model_validate(self.BODY)
        self.assertEqual({"top_k": 4, "min_similarity": 0.72, "temperature": 0.1}, payload.tuning())
        # Thân cũ hai trường vẫn hợp lệ, tham số thử để None = cấu hình mặc định.
        self.assertEqual({"top_k": None, "min_similarity": None, "temperature": None},
                         AskIn.model_validate({"query": "x"}).tuning())

    def test_askin_chan_gia_tri_ngoai_bien_va_truong_la(self):
        from pydantic import ValidationError

        from app.api.rest.routes.console_tools_controller import AskIn

        for bad in ({"top_k": 0}, {"top_k": 11}, {"temperature": 1.5}, {"temperature": -0.1},
                    {"min_similarity": 1.2}, {"max_tokens": 512}):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                AskIn.model_validate({**self.BODY, **bad})

    async def test_tham_so_thu_toi_copilot(self):
        svc, copilot, *_ = service()
        await svc.try_copilot(ML, "phí gửi xe?", None, top_k=4, min_similarity=0.72, temperature=0.1)
        request = copilot.ask_question.await_args.args[0]
        self.assertEqual((4, 0.72, 0.1), (request.top_k, request.min_similarity, request.temperature))

    def test_http_stream_khong_con_422(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api.rest import console_access
        from app.api.rest.routes import console_tools_controller as ctl

        seen = {}

        async def fake_stream(actor, query, parking_lot_id, **tuning):
            seen.update(tuning)
            yield SimpleNamespace(token="ok", is_finished=True, sources=[], confidence=None, refused=False,
                                  guardrail_triggered=None, prompt_version="v2", turn_id="t", latency_ms=1.0)

        app = FastAPI()
        app.include_router(ctl.router)
        with patch.object(ctl.console_tools_service, "try_copilot_stream", fake_stream), \
                patch.object(console_access.console_auth_service, "authorize_any", AsyncMock(return_value=ML)):
            response = TestClient(app).post("/tools/copilot/stream", json=self.BODY)
        self.assertEqual(200, response.status_code, response.text)
        self.assertIn('"token": "ok"', response.text)
        self.assertEqual({"top_k": 4, "min_similarity": 0.72, "temperature": 0.1}, seen)


class RagLimitsTest(unittest.TestCase):
    """Tham số thử chỉ làm truy xuất chặt hơn, không nới cổng NO_CONTEXT (ADR-0029)."""

    def test_min_similarity_khong_ha_duoi_cau_hinh(self):
        from app.core.copilot.engines.rag_pipeline import RagPipelineEngine

        engine = RagPipelineEngine(embedder=object(), vector_store=object(), llm=object())
        engine.top_k, engine.min_similarity = 5, 0.35
        self.assertEqual((5, 0.35), engine._limits(None, None))
        self.assertEqual((4, 0.72), engine._limits(4, 0.72))
        self.assertEqual((2, 0.35), engine._limits(2, 0.0))


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class ConsoleTryNotCountedTest(unittest.TestCase):
    def test_luot_thu_trong_console_khong_vao_so_muc_dung_san_pham(self):
        import psycopg2
        from psycopg2 import sql

        from app.infra.database.ai_request_log_store import AiRequestLogStore

        base = os.environ["AI_TEST_DATABASE_URL"]
        schema = "tools_" + uuid4().hex
        conn = psycopg2.connect(base)
        with conn, conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            sep = "&" if "?" in base else "?"
            store = AiRequestLogStore(f"{base}{sep}options=-csearch_path%3D{schema}", retention_days=30)
            for task in ("copilot_ask", "copilot_stream", CONSOLE_TRY_TASK, CONSOLE_TRY_TASK):
                asyncio.run(store.record({
                    "turn_id": str(uuid4()), "task": task, "status": "SUCCESS", "model": "m",
                    "model_revision": "", "prompt_version": "p", "tools": [], "input_tokens": 1,
                    "output_tokens": 1, "latency_ms": 10, "cost_usd": None, "user_hash": None,
                    "user_role": "member", "parking_lot_id": None, "query_redacted": "q",
                    "answer_redacted": "a", "error_code": None,
                }))
            self.assertEqual(2, asyncio.run(store.summary(7))["total_requests"])
            # Copilot Lab vẫn thấy cả lượt thử để chấm.
            self.assertEqual(4, len(asyncio.run(store.list_recent(10))))
        finally:
            with conn, conn.cursor() as cur:
                cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
            conn.close()


if __name__ == "__main__":
    unittest.main()
