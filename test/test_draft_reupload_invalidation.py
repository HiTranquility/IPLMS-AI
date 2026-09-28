"""PostgreSQL integration: replacing a draft must invalidate prior KB tests.

Set AI_TEST_DATABASE_URL to an isolated test database to run this test.
"""
import asyncio
import os
import unittest
from uuid import uuid4

from app.core.knowledge_eval.engines.gate import fingerprint, readiness
from app.infra.database.pgvector_client import PgVectorClient


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class DraftReuploadInvalidationTest(unittest.TestCase):
    def test_reupload_rotates_version_identity_and_blocks_old_run(self):
        import psycopg2

        url = os.environ["AI_TEST_DATABASE_URL"]
        vector = PgVectorClient(url)
        doc_id = str(uuid4())
        scope = f"draft-reupload-{uuid4()}"

        async def scenario():
            await vector.ensure_schema()
            base = {
                "document_id": doc_id,
                "file_name": "rules.txt",
                "category": "regulation",
                "parking_lot_id": scope,
                "uploaded_by": "test-owner",
            }
            embedding = [0.0] * vector.dimensions
            first = await vector.save_draft_version(
                **base,
                chunks=[{"content": "Old rule", "ordinal": 0, "embedding": embedding}],
            )
            second = await vector.save_draft_version(
                **base,
                chunks=[{"content": "New rule", "ordinal": 0, "embedding": embedding}],
            )
            current_ids = await vector.latest_version_ids(scope)
            return first, second, current_ids

        try:
            first, second, current_ids = asyncio.run(scenario())
            self.assertEqual(first["version_no"], second["version_no"])
            self.assertNotEqual(first["version_id"], second["version_id"])
            self.assertEqual([second["version_id"]], current_ids)
            old_run = {
                "status": "PASSED",
                "docs_fingerprint": fingerprint([first["version_id"]]),
                "suite_fingerprint": "same-suite",
            }
            reasons = readiness(old_run, fingerprint(current_ids), "same-suite", 1)
            self.assertTrue(any("Tài liệu đã thay đổi" in reason for reason in reasons))
            with psycopg2.connect(url) as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT v.status, c.content FROM knowledge_document_versions v "
                    "JOIN knowledge_chunks c ON c.version_id = v.id WHERE v.document_id = %s",
                    (doc_id,),
                )
                self.assertEqual([("DRAFT", "New rule")], cur.fetchall())
        finally:
            with psycopg2.connect(url) as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM knowledge_documents WHERE id = %s", (doc_id,))


if __name__ == "__main__":
    unittest.main()
