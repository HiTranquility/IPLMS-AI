"""Bộ eval Copilot (đề Final §4.2: ≥ 20 case normal/edge/should-refuse) giữ đúng schema.

Gộp 13 case của develop + 25 case của khoa-develop (IPLMS ADR-0049 §3). Chạy
retrieval bằng `python -m app.script.eval_retrieval`.
"""
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/knowledge/eval_set.json").read_text(encoding="utf-8"))
SEED_SOURCES = {
    c["source"] for c in json.loads((ROOT / "data/knowledge/regulations_seed.json").read_text(encoding="utf-8"))
}


class EvalSetTest(unittest.TestCase):
    def test_size_and_mix_meet_final_requirement(self):
        self.assertGreaterEqual(len(CASES), 20)
        mix = Counter(c["category"] for c in CASES)
        for category in ("normal", "edge", "should_refuse"):
            self.assertGreater(mix[category], 0, category)

    def test_schema_and_unique_ids(self):
        keys = {"id", "category", "expected_behavior", "question", "parking_lot_id", "expected_sources"}
        for case in CASES:
            self.assertEqual(keys, set(case), case.get("id"))
            self.assertIn(case["expected_behavior"], {"answer", "refuse"})
            self.assertTrue(case["question"].strip())
        self.assertEqual(len(CASES), len({c["id"] for c in CASES}))
        self.assertEqual(len(CASES), len({" ".join(c["question"].casefold().split()) for c in CASES}))

    def test_refuse_has_no_source_and_answer_is_runnable_on_seed(self):
        for case in CASES:
            if case["expected_behavior"] == "refuse":
                self.assertEqual([], case["expected_sources"], case["id"])
            else:
                self.assertTrue(set(case["expected_sources"]) & SEED_SOURCES, case["id"])


if __name__ == "__main__":
    unittest.main()
