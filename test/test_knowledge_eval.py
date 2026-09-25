"""Bộ test Knowledge Base (ISSUE-009): chấm tất định, cổng xuất bản, service chạy nền."""
import asyncio
import unittest

from app.core.exceptions import KnowledgeGateError, ModelNotLoadedError
from app.core.knowledge_eval.engines import case_generator, gate
from app.core.knowledge_eval.engines.grader import grade, is_refusal, normalize
from app.core.knowledge_eval.services.eval_service import KnowledgeEvalService


class NormalizeTest(unittest.TestCase):
    def test_money_and_time_formats_compare_equal(self):
        self.assertEqual(normalize("25.000 VNĐ"), normalize("25000đ"))
        self.assertEqual(normalize("25,000 đồng"), normalize("25.000đ"))
        self.assertEqual(normalize("20k"), normalize("20.000đ").replace("đ", ""))
        self.assertEqual(normalize("22h"), normalize("22:00"))
        self.assertEqual(normalize("22 giờ 30"), normalize("22:30"))

    def test_refusal_detection_ignores_accents(self):
        self.assertTrue(is_refusal("Mình chưa tìm thấy thông tin đủ liên quan trong kho tri thức"))
        self.assertTrue(is_refusal("Kho tri thức chưa có đủ thông tin để kết luận."))
        self.assertFalse(is_refusal("Phí gửi xe là 25.000đ mỗi giờ."))


class GradeTest(unittest.TestCase):
    def test_fact_passes_with_different_money_format(self):
        g = grade("fact", "Phí là 25.000 VNĐ/giờ [Nguồn: qc.pdf]", ["qc.pdf"], ["25000đ"], "qc.pdf")
        self.assertTrue(g.passed)

    def test_fact_fails_on_wrong_number(self):
        g = grade("fact", "Phí là 35.000đ/giờ", ["qc.pdf"], ["25.000đ"])
        self.assertFalse(g.passed)
        self.assertIn("25.000đ", g.reasons[0])

    def test_wrong_source_fails(self):
        g = grade("fact", "Phí là 25.000đ", ["khac.pdf"], ["25.000đ"], "qc.pdf")
        self.assertFalse(g.passed)

    def test_abstain_requires_refusal(self):
        self.assertTrue(grade("abstain", "", [], [], retrieved_nothing=True).passed)
        self.assertFalse(grade("abstain", "Bãi có hồ bơi miễn phí.", ["qc.pdf"], []).passed)

    def test_refusing_an_answerable_question_fails(self):
        g = grade("fact", "Mình chưa tìm thấy thông tin.", [], ["25.000đ"], retrieved_nothing=True)
        self.assertFalse(g.passed)

    def test_explain_asks_for_judge_only_after_deterministic_pass(self):
        self.assertTrue(grade("explain", "Nộp đơn trong 7 ngày", ["qc.pdf"], ["7 ngày"]).needs_judge)
        self.assertFalse(grade("explain", "Nộp đơn ngay", ["qc.pdf"], ["7 ngày"]).needs_judge)


class GateTest(unittest.TestCase):
    def test_verdict_thresholds(self):
        self.assertTrue(gate.run_verdict(10, 9, 0, 0, 5, 0.9)[0])
        self.assertFalse(gate.run_verdict(4, 4, 0, 0, 5, 0.9)[0])  # quá ít câu
        self.assertFalse(gate.run_verdict(10, 8, 0, 0, 5, 0.9)[0])  # dưới 90%
        self.assertFalse(gate.run_verdict(10, 9, 1, 0, 5, 0.9)[0])  # sai số liệu
        self.assertFalse(gate.run_verdict(10, 9, 0, 1, 5, 0.9)[0])  # không từ chối

    def test_readiness_blocks_stale_run(self):
        run = {"status": "PASSED", "docs_fingerprint": "a", "suite_fingerprint": "b", "verdict_reasons": []}
        self.assertEqual([], gate.readiness(run, "a", "b", unpublished_in_run=1))
        self.assertTrue(gate.readiness(run, "CHANGED", "b", 1))
        self.assertTrue(gate.readiness(run, "a", "CHANGED", 1))
        self.assertTrue(gate.readiness(run, "a", "b", 0))
        self.assertTrue(gate.readiness(None, "a", "b", 1))

    def test_fingerprint_ignores_order(self):
        self.assertEqual(gate.fingerprint(["b", "a"]), gate.fingerprint(["a", "b"]))


class CleanProposalsTest(unittest.TestCase):
    def test_drops_invalid_and_unknown_sources(self):
        payload = {
            "cases": [
                {"question": "Phí?", "expected_answer": "25.000đ", "expected_facts": ["25.000đ"], "expected_source": "qc.pdf", "kind": "fact"},
                {"question": "Phí?", "expected_answer": "trùng", "expected_facts": [], "expected_source": "", "kind": "fact"},
                {"question": "Có hồ bơi?", "expected_answer": "Không có", "expected_facts": ["x"], "expected_source": "qc.pdf", "kind": "abstain"},
                {"question": "Lạ", "expected_answer": "", "expected_facts": [], "expected_source": "bịa.pdf", "kind": "explain"},
                {"question": "", "expected_answer": "", "expected_facts": [], "expected_source": "", "kind": "fact"},
                {"question": "Sai loại", "expected_answer": "", "expected_facts": [], "expected_source": "", "kind": "other"},
            ]
        }
        out = case_generator.clean_proposals(payload, {"qc.pdf"}, 10)
        self.assertEqual(["Phí?", "Có hồ bơi?", "Lạ"], [c["question"] for c in out])
        self.assertEqual([], out[1]["expected_facts"])  # abstain không có fact
        self.assertEqual("", out[2]["expected_source"])  # nguồn bịa bị bỏ
        self.assertTrue(all(c["created_by"] == "ai" for c in out))


# ── Service với fake (không DB, không mạng) ─────────────────────────────────
class FakeStore:
    def __init__(self, cases):
        self.cases = cases
        self.runs = {}
        self.results = []

    async def list_cases(self, scope):
        return list(self.cases)

    async def create_run(self, scope, started_by, total, version_ids, docs_fingerprint, suite_fingerprint, max_concurrent):
        run = {"id": "run-1", "status": "RUNNING", "total": total, "done": 0, "passed": 0,
               "failed_facts": 0, "failed_abstain": 0, "verdict_reasons": [], "error": "",
               "version_ids": version_ids, "docs_fingerprint": docs_fingerprint,
               "suite_fingerprint": suite_fingerprint}
        self.runs[run["id"]] = run
        return dict(run)

    async def add_result(self, run_id, ordinal, result):
        self.results.append(result)

    async def finish_run(self, run_id, status, failed_facts=0, failed_abstain=0, verdict_reasons=None, error=""):
        self.runs[run_id].update(status=status, failed_facts=failed_facts, failed_abstain=failed_abstain,
                                 verdict_reasons=verdict_reasons or [], error=error)

    async def list_runs(self, scope, limit=20):
        return [dict(r) for r in self.runs.values()][:limit]

    async def count_unpublished(self, version_ids):
        return len(version_ids)


class FakeVectors:
    def __init__(self):
        self.tested = None
        self.published = None

    async def latest_version_ids(self, scope):
        return ["v2"]

    async def mark_versions_tested(self, ids, ok):
        self.tested = (ids, ok)

    async def publish_versions(self, scope, ids, by):
        self.published = (scope, ids, by)
        return len(ids)


class FakeRag:
    def __init__(self, answers):
        self.answers = answers

    async def query(self, question, parking_lot_id=None, preview=False):
        assert preview, "lượt chạy test phải dùng bản xem trước"
        answer = self.answers[question]
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeLlm:
    async def generate_json(self, *args, **kwargs):
        return {"verdict": "PASS", "reason": "đúng ý"}


def _case(i, kind="fact", facts=("25.000đ",)):
    return {"id": f"c{i}", "question": f"q{i}", "kind": kind, "expected_answer": "đáp án",
            "expected_facts": list(facts), "expected_source": "", "updated_at": "t"}


async def _drain(service):
    while service._tasks:
        await asyncio.gather(*list(service._tasks))


class EvalServiceTest(unittest.TestCase):
    def _service(self, cases, answers):
        store, vectors = FakeStore(cases), FakeVectors()
        return KnowledgeEvalService(store, vectors, FakeRag(answers), FakeLlm()), store, vectors

    def test_passing_run_marks_tested_and_unlocks_publish(self):
        cases = [_case(i) for i in range(5)] + [_case(9, "abstain", ())]
        answers = {f"q{i}": {"answer": "Phí 25.000 VNĐ", "sources": ["qc.pdf"]} for i in range(5)}
        answers["q9"] = {"answer": "chưa tìm thấy", "sources": []}
        service, store, vectors = self._service(cases, answers)

        async def scenario():
            await service.start_run("lot-a", "owner-1")
            await _drain(service)
            state = await service.readiness("lot-a")
            published = await service.publish("lot-a", "owner-1")
            return state, published

        state, published = asyncio.run(scenario())
        self.assertEqual("PASSED", store.runs["run-1"]["status"])
        self.assertEqual((["v2"], True), vectors.tested)
        self.assertTrue(state["ready"], state["reasons"])
        self.assertEqual(1, published)
        self.assertEqual(("lot-a", ["v2"], "owner-1"), vectors.published)

    def test_one_wrong_fee_blocks_publish(self):
        cases = [_case(i) for i in range(10)]
        answers = {f"q{i}": {"answer": "Phí 25.000đ", "sources": ["qc.pdf"]} for i in range(10)}
        answers["q3"] = {"answer": "Phí 35.000đ", "sources": ["qc.pdf"]}
        service, store, vectors = self._service(cases, answers)

        async def scenario():
            await service.start_run("lot-a", "owner-1")
            await _drain(service)
            with self.assertRaises(KnowledgeGateError):
                await service.publish("lot-a", "owner-1")

        asyncio.run(scenario())
        run = store.runs["run-1"]
        self.assertEqual(("FAILED", 1), (run["status"], run["failed_facts"]))
        self.assertIsNone(vectors.published)
        self.assertEqual([False], [r["passed"] for r in store.results if r["question"] == "q3"])

    def test_missing_llm_key_fails_run_as_infrastructure_not_as_wrong_answers(self):
        cases = [_case(i) for i in range(5)]
        answers = {f"q{i}": ModelNotLoadedError("chưa cấu hình khoá") for i in range(5)}
        service, store, _ = self._service(cases, answers)

        async def scenario():
            await service.start_run(None, "admin-1")
            await _drain(service)

        asyncio.run(scenario())
        run = store.runs["run-1"]
        self.assertEqual("FAILED", run["status"])
        self.assertIn("chưa cấu hình khoá", run["error"])
        self.assertEqual([], store.results)

    def test_empty_suite_is_rejected(self):
        service, _, _ = self._service([], {})
        with self.assertRaises(KnowledgeGateError):
            asyncio.run(service.start_run("lot-a", "owner-1"))

    def test_fact_case_requires_facts(self):
        service, _, _ = self._service([], {})
        with self.assertRaises(ValueError):
            asyncio.run(service.upsert_case({"question": "Phí?", "kind": "fact", "expected_facts": []}, "u"))


if __name__ == "__main__":
    unittest.main()
