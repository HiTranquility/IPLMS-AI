"""Telemetry Copilot (IPLMS ADR-0049): che PII, usage service, ghi lượt, token, store thật."""
import asyncio
import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.core.copilot.dtos.copilot_dto import AskQuestionRequest
from app.core.copilot.guardrails.pii_redactor import redact
from app.core.copilot.engines.rag_pipeline import NO_CONTEXT_ANSWER, PROMPT_VERSION, RagPipelineEngine
from app.core.copilot.services.usage_service import UsageService
from app.infra.llm.llm_factory import LlmFactory

UUID = re.compile(r"^[0-9a-f-]{36}$")


def run(coro):
    return asyncio.run(coro)


def cfg(**overrides):
    base = {"enabled": True, "hmac_key": "k", "retention_days": 30,
            "price_input_per_mtok": None, "price_output_per_mtok": None}
    return SimpleNamespace(**{**base, **overrides})


def request(query="Biển 51H-123.45 đỗ quá giờ phí bao nhiêu?"):
    return AskQuestionRequest(query=query, user_id="u-1", user_role="member", parking_lot_id="lot-1")


class RedactTest(unittest.TestCase):
    def test_masks_personal_data_but_keeps_tariffs(self):
        text = "Xe 51H-123.45, gọi 0901 234 567, mail a@b.vn, CCCD 079123456789; phí 35.000đ, Điều 9"
        out = redact(text)
        for leaked in ("51H-123.45", "0901 234 567", "a@b.vn", "079123456789"):
            self.assertNotIn(leaked, out)
        self.assertIn("35.000đ", out)
        self.assertIn("Điều 9", out)


class UsageServiceTest(unittest.TestCase):
    def test_user_hash_needs_key_and_is_stable(self):
        self.assertIsNone(UsageService(AsyncMock(), cfg(hmac_key="")).user_hash("u-1"))
        service = UsageService(AsyncMock(), cfg())
        self.assertEqual(service.user_hash("u-1"), service.user_hash("u-1"))
        self.assertNotEqual(service.user_hash("u-1"), service.user_hash("u-2"))
        self.assertNotIn("u-1", service.user_hash("u-1"))

    def test_cost_is_unknown_without_prices(self):
        self.assertIsNone(UsageService(AsyncMock(), cfg()).cost(1000, 500))
        priced = UsageService(AsyncMock(), cfg(price_input_per_mtok=2.0, price_output_per_mtok=8.0))
        self.assertAlmostEqual(0.006, priced.cost(1000, 500))
        self.assertIsNone(priced.cost(None, 500))  # provider không báo token → không đoán

    def test_entry_is_redacted_and_versioned(self):
        service = UsageService(AsyncMock(), cfg())
        entry = service.build_entry(
            turn_id="t", task="copilot_ask", status="SUCCESS", started=0.0, request=request(),
            result={"usage": {"input_tokens": 10, "output_tokens": 4}, "model": "m", "model_revision": "r"},
            answer="Xe 51H-123.45 trả 35.000đ",
        )
        self.assertNotIn("51H-123.45", entry["query_redacted"] + entry["answer_redacted"])
        self.assertEqual(PROMPT_VERSION, entry["prompt_version"])
        self.assertEqual((10, 4), (entry["input_tokens"], entry["output_tokens"]))
        self.assertEqual(["knowledge_search"], entry["tools"])
        error = service.build_entry(turn_id="t", task="copilot_ask", status="ERROR", started=0.0,
                                    request=request(), error_code="RagPipelineError")
        self.assertEqual([], error["tools"])

    def test_record_failure_never_breaks_request_and_disabled_skips(self):
        store = AsyncMock()
        store.record.side_effect = RuntimeError("db down")
        service = UsageService(store, cfg())

        async def scenario():
            service.record_soon({"turn_id": "x"})
            await service.drain()

        run(scenario())  # không ném lỗi
        store.record.assert_awaited_once()
        silent = UsageService(AsyncMock(), cfg(enabled=False))
        run(self._record_and_drain(silent))
        silent.store.record.assert_not_awaited()

    async def _record_and_drain(self, service):
        service.record_soon({"turn_id": "x"})
        await service.drain()

    def test_feedback_validation_and_owner_hash(self):
        store = AsyncMock()
        store.set_feedback.return_value = True
        service = UsageService(store, cfg())
        turn = str(uuid4())
        with self.assertRaises(ValueError):
            run(service.feedback(turn, "u-1", 5))
        with self.assertRaises(ValueError):
            run(service.feedback("không-phải-uuid", "u-1", 1))
        self.assertTrue(run(service.feedback(turn, "u-1", -1)))
        store.set_feedback.assert_awaited_once_with(turn, service.user_hash("u-1"), -1)
        no_key = UsageService(AsyncMock(), cfg(hmac_key=""))
        self.assertFalse(run(no_key.feedback(turn, "u-1", 1)))
        no_key.store.set_feedback.assert_not_awaited()

    def test_summary_window_bounds(self):
        service = UsageService(AsyncMock(), cfg())
        for days in (0, 91):
            with self.assertRaises(ValueError):
                run(service.summary(days))


# ── CopilotService ghi đúng lượt ──────────────────────────────────────────────

class _Recorder:
    def __init__(self):
        self.entries = []


class CopilotServiceTelemetryTest(unittest.TestCase):
    def setUp(self):
        from app.core.copilot.services import copilot_service as module

        self.module = module
        self.store = AsyncMock()
        self.usage = UsageService(self.store, cfg())
        self.patches = [patch.object(module, "usage_service", self.usage)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def recorded(self):
        return [call.args[0] for call in self.store.record.await_args_list]

    def test_ask_returns_turn_and_records_status_tokens(self):
        result = {"answer": "Phí 20.000đ [Nguồn: a.md]", "sources": ["a.md"], "confidence": 0.9,
                  "status": "SUCCESS", "usage": {"input_tokens": 12, "output_tokens": 6},
                  "model": "gpt-x", "model_revision": "copilot_answer:3"}

        async def scenario():
            with patch.object(self.module.rag_pipeline, "query", AsyncMock(return_value=result)):
                answer = await self.module.copilot_service.ask_question(request())
            await self.usage.drain()
            return answer

        answer = run(scenario())
        self.assertRegex(answer.turn_id, UUID)
        self.assertEqual(PROMPT_VERSION, answer.prompt_version)
        [entry] = self.recorded()
        self.assertEqual((answer.turn_id, "SUCCESS", 12, 6, "gpt-x"),
                         (entry["turn_id"], entry["status"], entry["input_tokens"],
                          entry["output_tokens"], entry["model"]))

    def test_ask_error_is_recorded_then_raised(self):
        async def scenario():
            with patch.object(self.module.rag_pipeline, "query", AsyncMock(side_effect=RuntimeError("x"))):
                with self.assertRaises(RuntimeError):
                    await self.module.copilot_service.ask_question(request())
            await self.usage.drain()

        run(scenario())
        [entry] = self.recorded()
        self.assertEqual(("ERROR", "RuntimeError"), (entry["status"], entry["error_code"]))

    def test_stream_puts_turn_on_last_chunk_and_records_once(self):
        async def fake_stream(*args, **kwargs):
            yield {"token": "Phí ", "is_finished": False, "sources": []}
            yield {"token": "", "is_finished": True, "sources": ["a.md"], "status": "REFUSED",
                   "usage": {"input_tokens": 3, "output_tokens": 2}, "model": "m", "answer": "Phí "}

        async def scenario():
            with patch.object(self.module.rag_pipeline, "stream_query", fake_stream):
                chunks = [c async for c in self.module.copilot_service.stream_answer(request())]
            await self.usage.drain()
            return chunks

        chunks = run(scenario())
        self.assertEqual("", chunks[0].turn_id)
        self.assertRegex(chunks[-1].turn_id, UUID)
        self.assertEqual(PROMPT_VERSION, chunks[-1].prompt_version)
        [entry] = self.recorded()
        self.assertEqual(("REFUSED", chunks[-1].turn_id), (entry["status"], entry["turn_id"]))

    def test_stream_error_midway_is_recorded(self):
        async def broken_stream(*args, **kwargs):
            yield {"token": "Phí ", "is_finished": False, "sources": []}
            raise RuntimeError("provider cut")

        async def scenario():
            with patch.object(self.module.rag_pipeline, "stream_query", broken_stream):
                with self.assertRaises(RuntimeError):
                    async for _ in self.module.copilot_service.stream_answer(request()):
                        pass
            await self.usage.drain()

        run(scenario())
        self.assertEqual(["ERROR"], [e["status"] for e in self.recorded()])


# ── Pipeline + LLM factory báo trạng thái và token ────────────────────────────

class _Embedder:
    async def embed_query(self, text):
        return [0.1]


class _Store:
    def __init__(self, chunks):
        self.chunks = chunks

    async def search_similar_chunks(self, *args, **kwargs):
        return self.chunks


class _Factory(LlmFactory):
    def __init__(self, answer):
        super().__init__(client=object())
        self.model, self.answer = "fake-model", answer

    async def generate_response(self, system_prompt, user_query, context, usage=None):
        usage.update(input_tokens=7, output_tokens=3)
        return self.answer


CHUNKS = [{"content": "Phí 20.000đ", "source": "quy-che.md", "similarity": 0.9}]


class PipelineStatusTest(unittest.TestCase):
    def test_no_context(self):
        result = run(RagPipelineEngine(_Embedder(), _Store([]), _Factory("x"), demo_seed_enabled=False).query("phí?"))
        self.assertEqual(("NO_CONTEXT", NO_CONTEXT_ANSWER), (result["status"], result["answer"]))

    def test_success_carries_usage_and_model(self):
        engine = RagPipelineEngine(_Embedder(), _Store(CHUNKS), _Factory("Phí 20.000đ [Nguồn: quy-che.md]"))
        result = run(engine.query("phí?", llm_override=engine.llm))
        self.assertEqual("SUCCESS", result["status"])
        self.assertEqual({"input_tokens": 7, "output_tokens": 3}, result["usage"])
        self.assertEqual("fake-model", result["model"])

    def test_guard_refusal_is_refused(self):
        engine = RagPipelineEngine(_Embedder(), _Store(CHUNKS), _Factory("Gửi xe miễn phí cả ngày."))
        result = run(engine.query("phí?", llm_override=engine.llm))
        self.assertEqual("REFUSED", result["status"])


class LlmUsageTest(unittest.TestCase):
    def test_generate_and_stream_copy_provider_usage(self):
        usage_obj = SimpleNamespace(input_tokens=11, output_tokens=5)

        class Responses:
            async def create(self, **kwargs):
                if kwargs.get("stream"):
                    async def events():
                        yield SimpleNamespace(type="response.output_text.delta", delta="ok")
                        yield SimpleNamespace(type="response.completed",
                                              response=SimpleNamespace(usage=usage_obj))
                    return events()
                return SimpleNamespace(output_text="ok", usage=usage_obj)

        factory = LlmFactory(client=SimpleNamespace(responses=Responses()))
        usage = {}
        self.assertEqual("ok", run(factory.generate_response("s", "q", "c", usage=usage)))
        self.assertEqual({"input_tokens": 11, "output_tokens": 5}, usage)

        async def collect():
            got = {}
            text = "".join([t async for t in factory.stream_response("s", "q", "c", usage=got)])
            return text, got

        self.assertEqual(("ok", {"input_tokens": 11, "output_tokens": 5}), run(collect()))


class GrpcHandlerTest(unittest.TestCase):
    def test_usage_summary_and_feedback_rpcs(self):
        from app.api.grpc.generated_stubs import get_stub
        from app.api.grpc.handlers import copilot_handler
        from app.core.copilot.dtos.copilot_dto import UsageDay, UsageSummary

        pb2, _ = get_stub("copilot_service")
        summary = UsageSummary(
            window_days=7, total_requests=2, success_requests=1, refused_requests=1,
            no_context_requests=0, error_requests=0, avg_latency_ms=10.0, p95_latency_ms=20.0,
            input_tokens=5, output_tokens=3, cost_known=False, total_cost_usd=0.0, avg_cost_usd=0.0,
            thumbs_up=0, thumbs_down=1,
            days=[UsageDay(date="2026-10-16", requests=2, errors=0, refused=1, avg_latency_ms=10.0)],
        )
        fake = AsyncMock()
        fake.summary.return_value = summary
        fake.feedback.return_value = True
        handler = copilot_handler.CopilotHandler()
        with patch.object(copilot_handler, "usage_service", fake):
            reply = run(handler.GetUsageSummary(pb2.UsageSummaryRequest(), None))
            ok = run(handler.RecordFeedback(pb2.RecordFeedbackRequest(turn_id="t", user_id="u", rating=-1), None))
        fake.summary.assert_awaited_once_with(7)  # days = 0 → mặc định 7
        self.assertEqual((2, False, "2026-10-16"), (reply.total_requests, reply.cost_known, reply.days[0].date))
        self.assertTrue(ok.recorded)
        fake.feedback.assert_awaited_once_with("t", "u", -1)


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class AiRequestLogStoreDatabaseTest(unittest.TestCase):
    def setUp(self):
        import psycopg2
        from psycopg2 import sql

        from app.infra.database.ai_request_log_store import AiRequestLogStore

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        self.schema = "ai_log_test_" + uuid4().hex
        self.admin = psycopg2.connect(base_url)
        with self.admin, self.admin.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        sep = "&" if "?" in base_url else "?"
        self.store = AiRequestLogStore(f"{base_url}{sep}options=-csearch_path%3D{self.schema}", 30)
        self.service = UsageService(self.store, cfg(price_input_per_mtok=1.0, price_output_per_mtok=2.0))

    def tearDown(self):
        from psycopg2 import sql

        with self.admin, self.admin.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def entry(self, status, latency, tokens=(100, 50), user="u-1"):
        e = self.service.build_entry(
            turn_id=str(uuid4()), task="copilot_ask", status=status, started=0.0,
            request=AskQuestionRequest(query="q", user_id=user),
            result={"usage": {"input_tokens": tokens[0], "output_tokens": tokens[1]}, "model": "m"},
            answer="a",
        )
        e["latency_ms"] = latency
        return e

    def test_summary_feedback_and_cost(self):
        entries = [self.entry("SUCCESS", 100), self.entry("SUCCESS", 200),
                   self.entry("REFUSED", 300), self.entry("ERROR", 1000, tokens=(0, 0))]
        for e in entries:
            run(self.store.record(e))
        turn = entries[0]["turn_id"]
        self.assertFalse(run(self.service.feedback(turn, "người-khác", 1)))  # không phải chủ lượt
        self.assertTrue(run(self.service.feedback(turn, "u-1", 1)))

        s = run(self.service.summary(7))
        self.assertEqual((4, 2, 1, 1), (s.total_requests, s.success_requests,
                                        s.refused_requests, s.error_requests))
        self.assertEqual(400.0, s.avg_latency_ms)
        self.assertEqual(895.0, s.p95_latency_ms)  # nội suy tuyến tính như PERCENTILE_CONT
        self.assertEqual((300, 150), (s.input_tokens, s.output_tokens))
        self.assertTrue(s.cost_known)
        self.assertAlmostEqual(3 * (100 / 1e6 + 50 * 2 / 1e6), s.total_cost_usd, places=6)
        self.assertEqual((1, 0), (s.thumbs_up, s.thumbs_down))
        self.assertEqual(4, sum(d.requests for d in s.days))

        unpriced = UsageService(self.store, cfg())
        run(self.store.record(unpriced.build_entry(
            turn_id=str(uuid4()), task="copilot_ask", status="SUCCESS", started=0.0,
            request=AskQuestionRequest(query="q", user_id="u-1"), result={}, answer="a")))
        self.assertFalse(run(self.service.summary(7)).cost_known)  # có lượt chưa biết giá → "—"


if __name__ == "__main__":
    unittest.main()
