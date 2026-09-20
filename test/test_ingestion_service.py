import asyncio
import unittest

from app.core.enums import IngestStatus
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand
from app.core.knowledge.services.ingestion_service import IngestionService


class FakeEmbedder:
    async def embed_texts(self, texts):
        return [[0.1, 0.2] for _ in texts]


class FakeStore:
    def __init__(self):
        self.saved = None

    async def replace_document(self, **kwargs):
        self.saved = kwargs


class IngestionServiceTest(unittest.TestCase):
    def test_parse_chunk_embed_and_store(self):
        store = FakeStore()
        service = IngestionService(FakeEmbedder(), store)
        command = IngestDocumentCommand(
            file_data=("# Điều 1\n\n" + "Quy định gửi xe hợp lệ. " * 20).encode(),
            file_name="quy-che.md",
            parking_lot_id="lot-a",
            category="regulation",
            uploaded_by="owner-a",
        )
        result = asyncio.run(service.ingest(command))
        self.assertEqual(IngestStatus.SUCCESS, result.status)
        self.assertGreater(result.chunk_count, 0)
        self.assertEqual("lot-a", store.saved["parking_lot_id"])
        self.assertEqual([0.1, 0.2], store.saved["chunks"][0]["embedding"])

    def test_rejects_unsupported_file_without_writing(self):
        store = FakeStore()
        service = IngestionService(FakeEmbedder(), store)
        result = asyncio.run(
            service.ingest(
                IngestDocumentCommand(file_data=b"abc", file_name="malware.exe")
            )
        )
        self.assertEqual(IngestStatus.UNSUPPORTED_FORMAT, result.status)
        self.assertIsNone(store.saved)


if __name__ == "__main__":
    unittest.main()
