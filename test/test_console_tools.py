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
