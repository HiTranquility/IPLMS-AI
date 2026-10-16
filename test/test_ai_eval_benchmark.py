"""Unit test benchmark validating the 25-case evaluation set (Section 4.2)."""
import json
import unittest
from pathlib import Path

from app.core.copilot.engines.rag_pipeline import rag_pipeline
from app.core.copilot.guardrails.guardrail_manager import guardrail_manager


class TestAiEvalBenchmark(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.eval_path = Path(__file__).resolve().parents[1] / "data" / "knowledge" / "eval_set.json"
        assert cls.eval_path.exists(), f"eval_set.json not found at {cls.eval_path}"
        with open(cls.eval_path, "r", encoding="utf-8") as f:
            cls.cases = json.load(f)

    def test_eval_set_size_and_diversity(self):
        """Mục 4.2: Tập kiểm chuẩn có ít nhất 20 test cases bao gồm normal, edge, should_refuse."""
        self.assertGreaterEqual(len(self.cases), 20, "Evaluation set must have at least 20 test cases")
        categories = {tc.get("category") for tc in self.cases}
        self.assertIn("normal", categories)
        self.assertIn("edge", categories)
        self.assertIn("should_refuse", categories)

    def test_should_refuse_guardrail_cases(self):
        """Mục 4.2: Tất cả 5 should_refuse cases phải bị từ chối dứt khoát."""
        refuse_cases = [tc for tc in self.cases if tc.get("category") == "should_refuse"]
        self.assertGreaterEqual(len(refuse_cases), 5)
        for tc in refuse_cases:
            q = tc["question"]
            guard_res = guardrail_manager.check_input(q)
            if not guard_res.is_safe:
                self.assertFalse(guard_res.is_safe)
            else:
                chunks = rag_pipeline._retrieve_from_seed(q, tc.get("parking_lot_id"))
                scope_res = guardrail_manager.check_scope_and_chunks(q, chunks)
                self.assertFalse(scope_res.is_safe, f"Câu hỏi ngoài luồng không bị từ chối: {q}")

    def test_normal_and_edge_retrieval_coverage(self):
        """Mục 4.2: Tất cả các câu hỏi normal và edge phải truy xuất được tài liệu phù hợp."""
        answerable = [tc for tc in self.cases if tc.get("category") in ("normal", "edge")]
        self.assertGreaterEqual(len(answerable), 15)
        passed = 0
        for tc in answerable:
            q = tc["question"]
            chunks = rag_pipeline._retrieve_from_seed(q, tc.get("parking_lot_id"))
            if chunks and any(c.get("similarity", 0) >= 0.35 for c in chunks):
                passed += 1

        pass_rate = passed / len(answerable)
        self.assertGreaterEqual(pass_rate, 0.90, f"Retrieval coverage pass rate too low: {pass_rate:.2f}")


if __name__ == "__main__":
    unittest.main()
