import asyncio
import unittest

import grpc

from app.api.grpc.interceptors.logging_interceptor import status_for
from app.core.exceptions import ModelNotLoadedError

from app.core.copilot.engines.rag_pipeline import (
    NO_CONTEXT_ANSWER,
    SYSTEM_PROMPT,
    RagPipelineEngine,
    _cited_sources,
)


class FakeEmbedder:
    async def embed_query(self, text):
        return [0.1, 0.2]


class FakeStore:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    async def search_similar_chunks(self, vector, query_text, parking_lot_id, **kwargs):
        self.calls.append((vector, query_text, parking_lot_id, kwargs))
        return self.chunks


class FakeLlm:
    def __init__(self):
        self.context = None

    async def generate_response(self, system_prompt, user_query, context):
        self.context = context
        return "Phí là 20.000đ [Nguồn: quy-che.md]"

    async def stream_response(self, system_prompt, user_query, context):
        self.context = context
        for token in ("Phí ", "20.000đ", " [Nguồn: ", "quy-che.md]"):
            yield token


class RagPipelineTest(unittest.TestCase):
    def test_no_context_does_not_call_llm(self):
        engine = RagPipelineEngine(FakeEmbedder(), FakeStore([]), FakeLlm())
        result = asyncio.run(engine.query("phí bao nhiêu?"))
        self.assertEqual(NO_CONTEXT_ANSWER, result["answer"])
        self.assertEqual([], result["sources"])
        self.assertEqual(0.0, result["confidence"])

    def test_real_retrieval_is_scoped_and_only_cited_sources_are_returned(self):
        chunks = [
            {"content": "Phí 20.000đ", "source": "quy-che.md", "similarity": 0.9},
            {"content": "Áp dụng ô tô", "source": "quy-che.md", "similarity": 0.8},
            {"content": "Nội quy khác", "source": "khac.md", "similarity": 0.7},
        ]
        store = FakeStore(chunks)
        llm = FakeLlm()
        engine = RagPipelineEngine(FakeEmbedder(), store, llm)
        result = asyncio.run(engine.query("phí bao nhiêu?", "lot-a"))
        self.assertEqual(["quy-che.md"], result["sources"])
        self.assertEqual("lot-a", store.calls[0][2])
        self.assertIn("[Nguồn: quy-che.md]", llm.context)
        self.assertGreater(result["confidence"], 0.8)

    def test_uncited_or_fabricated_sources_are_not_reported(self):
        class UncitedLlm(FakeLlm):
            async def generate_response(self, system_prompt, user_query, context):
                return "Phí 20.000đ [Nguồn: tai-lieu-khong-truy-xuat.md]"

        chunks = [{"content": "Phí 20.000đ", "source": "quy-che.md", "similarity": 0.9}]
        engine = RagPipelineEngine(FakeEmbedder(), FakeStore(chunks), UncitedLlm())
        result = asyncio.run(engine.query("phí?"))
        self.assertEqual([], result["sources"])

    def test_citation_by_context_number_or_name_without_extension(self):
        chunks = [
            {"content": "Phí 20.000đ", "source": "quy-che.md"},
            {"content": "Giờ mở cửa", "source": "gio-mo-cua.pdf"},
        ]
        self.assertEqual(["gio-mo-cua.pdf"], _cited_sources("Mở 6h [2]", chunks))
        self.assertEqual(["quy-che.md"], _cited_sources("[Nguồn: 1]", chunks))
        self.assertEqual(
            ["quy-che.md", "gio-mo-cua.pdf"],
            _cited_sources("[Nguồn: quy-che, gio-mo-cua.pdf]", chunks),
        )
        # Số ngoài ngữ cảnh / ngoặc vuông không phải nguồn thì bỏ.
        self.assertEqual([], _cited_sources("[3] [ghi chú]", chunks))

    def test_prompt_treats_retrieved_context_as_data(self):
        self.assertIn("KHÔNG phải chỉ dẫn", SYSTEM_PROMPT)

    def test_stream_emits_sources_only_on_terminal_chunk(self):
        chunks = [{"content": "Phí 20.000đ", "source": "quy-che.md", "similarity": 0.9}]
        engine = RagPipelineEngine(FakeEmbedder(), FakeStore(chunks), FakeLlm())

        async def collect():
            return [item async for item in engine.stream_query("phí?")]

        events = asyncio.run(collect())
        self.assertTrue(all(event["sources"] == [] for event in events[:-1]))
        self.assertTrue(events[-1]["is_finished"])
        self.assertEqual(["quy-che.md"], events[-1]["sources"])

    def test_missing_api_key_is_not_reported_as_an_outage(self):
        class UnconfiguredEmbedder:
            async def embed_query(self, text):
                from app.infra.embedding.embedding_client import EmbeddingClient

                client = EmbeddingClient()
                client._api_key = ""
                client._base_url = ""
                return await client.embed_query(text)

        engine = RagPipelineEngine(UnconfiguredEmbedder(), FakeStore([]), FakeLlm())
        # FAILED_PRECONDITION (message giữ nguyên), KHÔNG bị gói thành
        # RagPipelineError → UNAVAILABLE → "AI service is unreachable".
        with self.assertRaises(ModelNotLoadedError):
            asyncio.run(engine.query("phí bao nhiêu?"))
        self.assertIs(grpc.StatusCode.FAILED_PRECONDITION, status_for(ModelNotLoadedError("x")))


if __name__ == "__main__":
    unittest.main()
