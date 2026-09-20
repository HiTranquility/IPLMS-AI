import asyncio
import unittest
from types import SimpleNamespace

from app.infra.embedding.embedding_client import EmbeddingClient


class FakeEmbeddings:
    def __init__(self, dimensions):
        self.dimensions = dimensions
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        # Deliberately reverse API order; client must restore indexes.
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=i, embedding=[float(i)] * self.dimensions)
                for i in reversed(range(len(kwargs["input"])))
            ]
        )


class EmbeddingClientTest(unittest.TestCase):
    def test_batch_preserves_input_order_and_dimensions(self):
        probe = EmbeddingClient(client=SimpleNamespace(embeddings=SimpleNamespace()))
        fake = FakeEmbeddings(probe._config.dimensions)
        client = EmbeddingClient(client=SimpleNamespace(embeddings=fake))
        vectors = asyncio.run(client.embed_texts(["đoạn một", "đoạn hai"]))
        self.assertEqual(0.0, vectors[0][0])
        self.assertEqual(1.0, vectors[1][0])
        self.assertEqual(probe._config.dimensions, fake.calls[0]["dimensions"])

    def test_empty_input_does_not_call_api(self):
        fake = FakeEmbeddings(1536)
        client = EmbeddingClient(client=SimpleNamespace(embeddings=fake))
        self.assertEqual([], asyncio.run(client.embed_texts([])))
        self.assertEqual([], fake.calls)


if __name__ == "__main__":
    unittest.main()
