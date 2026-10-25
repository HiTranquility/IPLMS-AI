"""Unit tests for Copilot RAG evaluation datasets (eval_set and eval_set_heldout).

Enforces schema integrity, ID uniqueness, data leakage prevention,
and minimum dataset size (ISSUE-007).
"""
import json
from pathlib import Path
import unittest


class CopilotEvalDatasetTest(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).resolve().parents[1]
        self.eval_set_path = self.root_dir / "data" / "knowledge" / "eval_set.json"
        self.heldout_path = self.root_dir / "data" / "knowledge" / "eval_set_heldout.json"

    def test_eval_set_exists_and_valid(self):
        self.assertTrue(self.eval_set_path.is_file(), "eval_set.json không tồn tại")
        with open(self.eval_set_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(len(data), 20, "eval_set.json cần ít nhất 20 câu")

    def test_heldout_dataset_meets_minimum_size(self):
        self.assertTrue(self.heldout_path.is_file(), "eval_set_heldout.json không tồn tại")
        with open(self.heldout_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(
            len(data),
            30,
            f"Bộ held-out Copilot phải có ít nhất 30 câu (hiện có: {len(data)})",
        )

    def test_heldout_dataset_schema_and_values(self):
        with open(self.heldout_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = {"id", "category", "expected_behavior", "question", "parking_lot_id", "expected_sources"}
        seen_ids = set()
        seen_questions = set()

        for item in data:
            self.assertEqual(set(item.keys()), required_keys, f"Item thiếu keys: {item}")
            item_id = item["id"]
            self.assertTrue(item_id.startswith("HO-"), f"ID phải bắt đầu bằng HO-: {item_id}")
            self.assertNotIn(item_id, seen_ids, f"Trùng lặp ID: {item_id}")
            seen_ids.add(item_id)

            q = item["question"].strip()
            self.assertTrue(len(q) > 5, f"Câu hỏi quá ngắn: {q}")
            self.assertNotIn(q.lower(), seen_questions, f"Trùng lặp câu hỏi: {q}")
            seen_questions.add(q.lower())

            self.assertIn(
                item["category"],
                {"normal", "edge", "should_refuse"},
                f"category không hợp lệ: {item['category']}",
            )
            self.assertIn(
                item["expected_behavior"],
                {"answer", "refuse"},
                f"expected_behavior không hợp lệ: {item['expected_behavior']}",
            )

            if item["expected_behavior"] == "refuse":
                self.assertEqual(
                    item["expected_sources"],
                    [],
                    f"Câu hỏi từ chối ({item_id}) không được có expected_sources",
                )
            else:
                self.assertGreaterEqual(
                    len(item["expected_sources"]),
                    1,
                    f"Câu hỏi trả lời ({item_id}) phải có ít nhất 1 expected_source",
                )

    def test_no_data_leakage_between_train_and_heldout(self):
        """Đảm bảo không có câu hỏi nào trong tập held-out bị trùng với tập eval_set."""
        with open(self.eval_set_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        with open(self.heldout_path, "r", encoding="utf-8") as f:
            heldout_data = json.load(f)

        eval_questions = {item["question"].strip().lower() for item in eval_data}
        for item in heldout_data:
            q = item["question"].strip().lower()
            self.assertNotIn(
                q,
                eval_questions,
                f"Phát hiện rò rỉ dữ liệu (Data Leakage): '{item['question']}' xuất hiện ở cả 2 tập!",
            )


if __name__ == "__main__":
    unittest.main()
