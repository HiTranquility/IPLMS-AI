import asyncio
import unittest

from app.core.copilot.engines.output_guard import GUARD_NOTICE, guard_stream, violation
from app.core.copilot.engines.rag_pipeline import RagPipelineEngine

CONTEXT = (
    "[1] [Nguồn: quy-che-bai-A.pdf]\nPhí gửi ô tô: 25.000đ mỗi giờ. Xe máy: 5.000đ mỗi lượt. "
    "Mở cửa 06:00–22:00. Hotline 0901 234 567."
)


class ViolationTest(unittest.TestCase):
    def test_grounded_answers_pass(self):
        for answer in (
            "Gửi ô tô 3 giờ hết 75.000đ [Nguồn: quy-che-bai-A.pdf].",
            "Bãi mở cửa 06:00–22:00, gọi hotline 0901234567.",
            "Gửi tháng khoảng 12.500.000 đồng.",
            "Kho tri thức chưa có thông tin về xe đạp.",
        ):
            self.assertIsNone(violation(answer, CONTEXT), answer)

    def test_free_claim_not_in_context_is_blocked(self):
        self.assertEqual("free_claim", violation("Gửi ô tô MIỄN PHÍ.", CONTEXT))
        self.assertEqual("free_claim", violation("Phí gửi là 0đ.", CONTEXT))
        self.assertEqual("free_claim", violation("Bãi mở cửa m i ễ n   p h í hôm nay.", CONTEXT))
        self.assertEqual("free_claim", violation("Mọi xe đều m.i.ễ.n p.h.í.", CONTEXT))
        self.assertEqual("free_claim", violation("Hôm nay không thu phí gửi ô tô.", CONTEXT))
        self.assertIsNone(violation("Xe đạp miễn phí.", CONTEXT + " Xe đạp miễn phí."))

    def test_link_not_in_context_is_blocked(self):
        self.assertEqual("unknown_link", violation("Ưu đãi tại zalo.me/uudai nhé.", CONTEXT))
        self.assertEqual("unknown_link", violation("Xem https://evil.example/x", CONTEXT))

    def test_account_or_phone_not_in_context_is_blocked(self):
        self.assertEqual("unknown_number", violation("Chuyển khoản STK 0123456789.", CONTEXT))
        self.assertEqual("unknown_number", violation("Gọi 0988 777 666.", CONTEXT))


def _collect(tokens, context=CONTEXT):
    async def source():
        for token in tokens:
            yield token

    tripped = []

    async def run():
        return [t async for t in guard_stream(source(), context, tripped.append)]

    return asyncio.run(run()), tripped


class GuardStreamTest(unittest.TestCase):
    def test_clean_stream_releases_everything_in_order(self):
        tokens = ["Gửi ", "ô tô ", "3 giờ ", "hết ", "75.000đ ", "[Nguồn: ", "quy-che-bai-A.pdf]."] * 3
        out, tripped = _collect(tokens)
        self.assertEqual("".join(tokens), "".join(out))
        self.assertEqual([], tripped)

    def test_violation_stops_before_bad_text_is_released(self):
        tokens = ["Phí ", "ô tô ", "hiện ", "tại ", "là ", "MIỄN ", "PHÍ ", "từ ", "hôm ", "nay."]
        out, tripped = _collect(tokens)
        self.assertEqual(["free_claim"], tripped)
        self.assertNotIn("MIỄN", "".join(out))
        self.assertTrue("".join(out).endswith(GUARD_NOTICE))

    def test_known_number_split_across_tokens_is_not_blocked(self):
        tokens = ["Hotline ", "của ", "bãi ", "là ", "0901 ", "234 ", "56", "7."]
        out, tripped = _collect(tokens)
        self.assertEqual([], tripped)
        self.assertEqual("".join(tokens), "".join(out))

    def test_violation_in_last_token_is_still_blocked(self):
        out, tripped = _collect(["Gửi ", "ô tô ", "MIỄN PHÍ"])
        self.assertEqual(["free_claim"], tripped)
        self.assertNotIn("MIỄN", "".join(out))

    def test_long_link_is_not_leaked_by_halves(self):
        tokens = ["Xem ", "https://", "a" * 60, ".example/", "b" * 30, " nhé"]
        out, tripped = _collect(tokens)
        self.assertEqual(["unknown_link"], tripped)
        self.assertNotIn("https", "".join(out))


class FakeEmbedder:
    async def embed_query(self, text):
        return [0.1]


class FakeStore:
    async def search_similar_chunks(self, *args, **kwargs):
        return [{"content": "Phí gửi ô tô: 25.000đ mỗi giờ.", "source": "quy-che.md", "similarity": 0.9}]


class InjectedLlm:
    """Mô phỏng model đã bị câu hỏi giả 'ngữ cảnh' thuyết phục."""

    async def generate_response(self, system_prompt, user_query, context):
        return "Từ hôm nay gửi ô tô MIỄN PHÍ [Nguồn: quy-che.md]"

    async def stream_response(self, system_prompt, user_query, context, history=None):
        for token in ("Từ ", "hôm ", "nay ", "gửi ", "ô tô ", "MIỄN ", "PHÍ ", "[Nguồn: ", "quy-che.md]"):
            yield token


class RagPipelineGuardTest(unittest.TestCase):
    def setUp(self):
        self.engine = RagPipelineEngine(FakeEmbedder(), FakeStore(), InjectedLlm())

    def test_unary_answer_is_replaced_and_sources_dropped(self):
        result = asyncio.run(self.engine.query("Gửi ô tô bao nhiêu?"))
        self.assertEqual(GUARD_NOTICE, result["answer"])
        self.assertEqual([], result["sources"])
        self.assertEqual(0.0, result["confidence"])

    def test_stream_ends_with_notice_and_no_sources(self):
        async def run():
            return [c async for c in self.engine.stream_query("Gửi ô tô bao nhiêu?")]

        chunks = asyncio.run(run())
        text = "".join(c["token"] for c in chunks)
        self.assertNotIn("MIỄN", text)
        self.assertTrue(text.endswith(GUARD_NOTICE))
        self.assertTrue(chunks[-1]["is_finished"])
        self.assertEqual([], chunks[-1]["sources"])


if __name__ == "__main__":
    unittest.main()
