"""Copilot Lab của AI Console: quyền, kiểm đầu vào và chấm lượt trên Postgres thật (ISSUE-126 P1c)."""
import asyncio
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.core.console.dtos import ConsoleActor
from app.core.console.services.copilot_lab_service import ConsoleCopilotLabService
from app.core.exceptions import ConsoleAccessDenied

TURN = "3f1c2a64-5b7d-4e8f-9a01-23456789abcd"


def actor(*roles, member_id="m-1"):
    return ConsoleActor(member_id=member_id, roles=frozenset(roles))


def service(**overrides):
    request_log = AsyncMock()
    request_log.list_recent.return_value = [{"turn_id": TURN, "query": "phí?"}]
    request_log.turn_time.return_value = datetime.now(timezone.utc)
    store = AsyncMock()
    store.get_reviews.return_value = {}
    store.review_stats.return_value = {}
    usage = AsyncMock()
    deps = {"usage": usage, "request_log": request_log, "store": store, **overrides}
    return ConsoleCopilotLabService(**deps), deps


class CopilotLabPolicyTest(unittest.IsolatedAsyncioTestCase):
    async def test_annotator_khong_doc_duoc_chat_log(self):
        svc, _ = service()
        with self.assertRaises(ConsoleAccessDenied):
            await svc.list_turns(actor("ai_annotator"))

    async def test_analyst_doc_duoc_nhung_khong_cham_duoc(self):
        svc, deps = service()
        rows = await svc.list_turns(actor("ai_analyst"))
        self.assertEqual(rows[0]["review"], None)
        with self.assertRaises(ConsoleAccessDenied):
            await svc.review_turn(actor("ai_analyst"), TURN, "CORRECT")
        deps["store"].review_turn.assert_not_called()

    async def test_cham_sai_phai_co_ghi_chu(self):
        svc, deps = service()
        with self.assertRaisesRegex(ValueError, "ghi chú"):
            await svc.review_turn(actor("ai_reviewer"), TURN, "INCORRECT", " ")
        await svc.review_turn(actor("ai_reviewer"), TURN, "CORRECT")
        deps["store"].review_turn.assert_awaited_once()

    async def test_tu_choi_turn_id_verdict_va_moc_thoi_gian_sai(self):
        svc, _ = service()
        reviewer = actor("ai_reviewer")
        with self.assertRaises(ValueError):
            await svc.review_turn(reviewer, "abc", "CORRECT")
        with self.assertRaises(ValueError):
            await svc.review_turn(reviewer, TURN, "MAYBE")
        with self.assertRaises(ValueError):
            await svc.list_turns(reviewer, before="hôm qua")
        with self.assertRaises(ValueError):
            await svc.list_turns(reviewer, status="DROP TABLE")
        with self.assertRaises(ValueError):
            await svc.list_turns(reviewer, limit=0)

    async def test_luot_qua_han_luu_khong_cham_duoc(self):
        svc, deps = service()
        deps["request_log"].turn_time.return_value = None
        with self.assertRaisesRegex(ValueError, "hạn lưu"):
            await svc.review_turn(actor("ai_reviewer"), TURN, "CORRECT")

    async def test_ti_le_dung_chi_tinh_tren_luot_da_cham(self):
        svc, deps = service()
        self.assertIsNone((await svc.review_stats(actor("ai_analyst"), 7))["accuracy"])
        deps["store"].review_stats.return_value = {"CORRECT": 3, "INCORRECT": 1}
        stats = await svc.review_stats(actor("ai_analyst"), 7)
        self.assertEqual((stats["reviewed"], stats["accuracy"]), (4, 0.75))


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class CopilotLabStoreTest(unittest.TestCase):
    def setUp(self):
        import psycopg2
        from psycopg2 import sql

        from app.infra.database.ai_request_log_store import AiRequestLogStore
        from app.infra.database.console_store import ConsoleStore
        from app.infra.identity.password import hash_password

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        self.schema = "copilot_lab_" + uuid4().hex
        self.admin_conn = psycopg2.connect(base_url)
        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}options=-csearch_path%3D{self.schema}"
        self.console = ConsoleStore(url)
        self.log = AiRequestLogStore(url, retention_days=30)
        self.reviewer_id = asyncio.run(self.console.create_emergency_admin(
            "rv@x.vn", "Người chấm", hash_password("mật-khẩu-đủ-dài-123"), None, "ai_reviewer"
        ))
        self.svc = ConsoleCopilotLabService(usage=AsyncMock(), request_log=self.log, store=self.console)

    def tearDown(self):
        from psycopg2 import sql

        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin_conn.close()

    def _turn(self, status="SUCCESS", feedback=None):
        turn_id = str(uuid4())
        asyncio.run(self.log.record({
            "turn_id": turn_id, "task": "copilot_ask", "status": status, "model": "m",
            "model_revision": "r", "prompt_version": "p#1", "tools": ["knowledge_search"],
            "input_tokens": 10, "output_tokens": 5, "latency_ms": 120, "cost_usd": None,
            "user_hash": "a" * 64, "user_role": "member", "parking_lot_id": None,
            "query_redacted": "phí gửi xe [PLATE]?", "answer_redacted": "20.000đ",
            "error_code": None,
        }))
        if feedback is not None:
            asyncio.run(self.log.set_feedback(turn_id, "a" * 64, feedback))
        return turn_id

    def test_cham_lai_ghi_de_ket_qua_va_moi_lan_co_audit(self):
        reviewer = actor("ai_reviewer", member_id=self.reviewer_id)
        turn = self._turn()
        asyncio.run(self.svc.review_turn(reviewer, turn, "INCORRECT", "sai giá ngày lễ"))
        asyncio.run(self.svc.review_turn(reviewer, turn, "CORRECT"))

        rows = asyncio.run(self.svc.list_turns(reviewer))
        self.assertEqual(rows[0]["review"]["verdict"], "CORRECT")
        self.assertEqual(rows[0]["review"]["reviewer"], "Người chấm")
        self.assertNotIn("user_hash", rows[0])
        stats = asyncio.run(self.svc.review_stats(actor("ai_analyst"), 7))
        self.assertEqual((stats["reviewed"], stats["accuracy"]), (1, 1.0))
        actions = [e["action"] for e in asyncio.run(self.console.list_audit(10))]
        self.assertEqual(actions.count("copilot.review:INCORRECT"), 1)
        self.assertEqual(actions.count("copilot.review:CORRECT"), 1)

    def test_loc_theo_trang_thai_va_feedback(self):
        reviewer = actor("ai_reviewer", member_id=self.reviewer_id)
        self._turn("SUCCESS", feedback=-1)
        self._turn("REFUSED")
        self._turn("SUCCESS", feedback=1)
        self.assertEqual(len(asyncio.run(self.svc.list_turns(reviewer, status="REFUSED"))), 1)
        down = asyncio.run(self.svc.list_turns(reviewer, feedback=-1))
        self.assertEqual([r["feedback"] for r in down], [-1])
        newest = asyncio.run(self.svc.list_turns(reviewer, limit=1))
        older = asyncio.run(self.svc.list_turns(reviewer, before=newest[0]["at"]))
        self.assertEqual(len(older), 2)


if __name__ == "__main__":
    unittest.main()
