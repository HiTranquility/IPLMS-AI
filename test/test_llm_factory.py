import asyncio
import unittest
from types import SimpleNamespace

from app.infra.llm.llm_factory import LlmFactory


class FakeResponses:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            async def events():
                yield SimpleNamespace(type="response.created")
                yield SimpleNamespace(type="response.output_text.delta", delta="Xin ")
                yield SimpleNamespace(type="response.output_text.delta", delta="chào")
                yield SimpleNamespace(type="response.completed")
            return events()
        return SimpleNamespace(output_text="Câu trả lời có nguồn")


class LlmFactoryTest(unittest.TestCase):
    def setUp(self):
        self.responses = FakeResponses()
        self.factory = LlmFactory(client=SimpleNamespace(responses=self.responses))

    def test_unary_uses_responses_api_without_provider_storage(self):
        answer = asyncio.run(self.factory.generate_response("system", "question", "context"))
        self.assertEqual("Câu trả lời có nguồn", answer)
        self.assertFalse(self.responses.calls[0]["store"])
        self.assertIn("NGỮ CẢNH", self.responses.calls[0]["input"])

    def test_stream_yields_only_text_delta_events(self):
        async def collect():
            return [token async for token in self.factory.stream_response("s", "q", "c")]

        self.assertEqual(["Xin ", "chào"], asyncio.run(collect()))
        self.assertTrue(self.responses.calls[0]["stream"])


if __name__ == "__main__":
    unittest.main()
