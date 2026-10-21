import asyncio
import unittest
from uuid import UUID

from app.core.enums import IngestStatus
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand
from app.core.knowledge.services.ingestion_service import IngestionService


class FakeEmbedder:
    async def embed_texts(self, texts):
        return [[0.1, 0.2] for _ in texts]


class FakeStore:
    def __init__(self):
        self.saved = None

    async def save_draft_version(self, **kwargs):
        self.saved = kwargs
        return {"version_id": "v-1", "version_no": 1}


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

    def test_caller_document_id_makes_retry_replace_the_same_document(self):
        store = FakeStore()
        service = IngestionService(FakeEmbedder(), store)
        stable_id = UUID("d7e1375c-2cce-4a15-bd19-8ed62f9be944")
        command = IngestDocumentCommand(
            file_data=b"# Dieu 1\n\nNoi dung quy dinh bai xe.",
            file_name="quy-che.md",
            document_id=stable_id,
        )

        first = asyncio.run(service.ingest(command))
        second = asyncio.run(service.ingest(command))

        self.assertEqual(str(stable_id), first.document_id)
        self.assertEqual(first.document_id, second.document_id)
        self.assertEqual(str(stable_id), store.saved["document_id"])

    def test_list_passes_lot_scope_and_maps_rows(self):
        class ListingStore(FakeStore):
            async def list_documents(self, parking_lot_id):
                self.listed_scope = parking_lot_id
                return [
                    {
                        "document_id": "d1",
                        "file_name": "quy-che.pdf",
                        "category": "regulation",
                        "uploaded_by": None,
                        "chunk_count": 3,
                        "created_at": "2026-09-25T00:00:00+00:00",
                        "updated_at": "2026-09-25T00:00:00+00:00",
                    }
                ]

        store = ListingStore()
        documents = asyncio.run(IngestionService(FakeEmbedder(), store).list("lot-a"))

        self.assertEqual("lot-a", store.listed_scope)
        self.assertEqual("quy-che.pdf", documents[0].file_name)
        self.assertEqual(3, documents[0].chunk_count)


if __name__ == "__main__":
    unittest.main()
