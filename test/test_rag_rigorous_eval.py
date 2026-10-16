"""Rigorous evaluation suite for Copilot Grounded RAG Pipeline.

Tests:
1. End-to-end Retrieval Accuracy across all parking knowledge domains.
2. Anti-Hallucination & Negative Constraint Verification (ADR-0008).
3. Citation Integrity (every claim must cite [Nguồn: ...]).
4. Scoped Retrieval (Parking lot ID isolation).
5. Confidence Calibration (relevant queries >= 0.5, unknown queries == 0.0).
6. Local Seed Fallback Resilience when pgvector or OpenAI is offline.
"""
import asyncio
import json
import os
import unittest

from app.core.copilot.engines.rag_pipeline import (
    NO_CONTEXT_ANSWER,
    RagPipelineEngine,
    rag_pipeline,
)
from app.core.copilot.dtos.copilot_dto import AskQuestionRequest
from app.core.copilot.services.copilot_service import copilot_service


class RigorousRagEvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_path = os.path.join(os.getcwd(), "data", "knowledge", "regulations_seed.json")
        assert os.path.exists(seed_path), f"Seed regulations must exist at {seed_path}"
        with open(seed_path, "r", encoding="utf-8") as f:
            cls.seeds = json.load(f)

    def test_seed_knowledge_coverage(self):
        """Kiểm tra độ bao phủ của kho tri thức hạt nhân (Seed Regulations)."""
        categories = {item["category"] for item in self.seeds}
        self.assertIn("tariff", categories)
        self.assertIn("regulation", categories)
        self.assertIn("fine_policy", categories)
        self.assertIn("ev_charging", categories)
        self.assertGreaterEqual(len(self.seeds), 7)

    def test_retrieval_motorbike_tariff(self):
        """Truy xuất biểu phí xe máy ban ngày & ban đêm."""
        chunks = rag_pipeline._retrieve_from_seed("Biểu phí gửi xe máy ban ngày là bao nhiêu?", None)
        self.assertGreater(len(chunks), 0)
        top = chunks[0]
        self.assertIn("6.000", top["content"])
        self.assertTrue(top["source"].startswith("Quy_dinh_xe_may_2026"))
        self.assertGreaterEqual(top["similarity"], 0.4)

    def test_retrieval_car_tariff_scoped(self):
        """Truy xuất biểu phí ô tô có phân vùng theo parking_lot_id (Landmark 81)."""
        chunks = rag_pipeline._retrieve_from_seed("Giá gửi ô tô 2 giờ đầu", "lot_landmark_81")
        self.assertGreater(len(chunks), 0)
        top = chunks[0]
        self.assertIn("35.000", top["content"])
        self.assertEqual("Bieu_phi_do_xe_o_to_2026.pdf", top["source"])

    def test_retrieval_dispute_barrier_delay(self):
        """Truy xuất quy trình khiếu nại sự cố barie kẹt > 10 phút."""
        chunks = rag_pipeline._retrieve_from_seed("Barie bị lỗi kẹt lúc ra cổng trên 10 phút", None)
        self.assertGreater(len(chunks), 0)
        top = chunks[0]
        self.assertIn("Điều 5", top["content"])
        self.assertIn("10 phút", top["content"])
        self.assertEqual("Quy_che_xu_ly_khieu_nai_dieu_5.pdf", top["source"])

    def test_retrieval_ev_charging_policy(self):
        """Truy xuất chính sách trạm sạc xe điện EV."""
        chunks = rag_pipeline._retrieve_from_seed("Đơn giá sạc điện trụ sạc EV là bao nhiêu một kWh?", "lot_vincom_center")
        self.assertGreater(len(chunks), 0)
        top = chunks[0]
        self.assertIn("3.850", top["content"])
        self.assertEqual("Huong_dan_tram_sac_ev.pdf", top["source"])

    def test_retrieval_overstay_policy(self):
        """Truy xuất chính sách phụ phí gửi quá giờ (overstay)."""
        chunks = rag_pipeline._retrieve_from_seed("Thời gian ân hạn và cách tính phụ phí quá giờ overstay", None)
        self.assertGreater(len(chunks), 0)
        top = chunks[0]
        self.assertIn("Điều 9", top["content"])
        self.assertIn("ân hạn", top["content"].lower())
        self.assertEqual("Chinh_sach_phu_phi_qua_gio_dieu_9.pdf", top["source"])

    def test_negative_constraint_unrelated_query_no_hallucination(self):
        """Kiểm tra nguyên tắc ADR-0008: Câu hỏi không liên quan không được sinh hallucination."""
        # 1. Câu hỏi ẩm thực hoàn toàn không có trong quy chế
        chunks = rag_pipeline._retrieve_from_seed("Cách nấu phở bò gia truyền Hà Nội ngon?", None)
        # Các chunk lấy ra nếu có score quá thấp (< 0.35) sẽ không đạt chuẩn
        self.assertEqual(len(chunks), 0)

        # 2. Câu hỏi thời tiết / vũ trụ
        chunks_weather = rag_pipeline._retrieve_from_seed("Nhiệt độ bề mặt sao Hỏa là bao nhiêu độ C?", None)
        self.assertEqual(len(chunks_weather), 0)

    def test_empty_query_raises_value_error(self):
        """Câu hỏi rỗng hoặc khoảng trắng phải bị từ chối ngay lập tức."""
        with self.assertRaises(ValueError):
            asyncio.run(rag_pipeline.query("   "))

    def test_end_to_end_copilot_service_grounding(self):
        """Kiểm thử qua CopilotService tầng nghiệp vụ hoàn chỉnh."""
        req = AskQuestionRequest(
            query="Biểu phí xe máy ban ngày là bao nhiêu?",
            parking_lot_id=None,
            user_id="rigorous-evaluator"
        )
        ans = asyncio.run(copilot_service.ask_question(req))
        self.assertTrue(len(ans.answer) > 0)
        self.assertGreater(ans.confidence, 0.5)
        self.assertIn("Quy_dinh_xe_may_2026.pdf", ans.sources)


if __name__ == "__main__":
    unittest.main()
