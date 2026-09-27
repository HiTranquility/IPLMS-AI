"""Optional PostgreSQL integration test for the RAG publish race.

Set AI_TEST_DATABASE_URL to an isolated test database to run this test.
"""
import asyncio
import os
import threading
import time
import unittest
from uuid import uuid4

from app.core.exceptions import KnowledgeGateError
from app.core.knowledge_eval.engines.gate import fingerprint, suite_fingerprint
from app.infra.database.knowledge_eval_store import KnowledgeEvalStore
from app.infra.database.pgvector_client import PgVectorClient


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class PublishConcurrencyTest(unittest.TestCase):
    def test_rejected_review_wins_before_publish_gate(self):
        import psycopg2

        url = os.environ["AI_TEST_DATABASE_URL"]
        vector = PgVectorClient(url)
        store = KnowledgeEvalStore(url)
        asyncio.run(vector.ensure_schema())
        # KnowledgeEvalStore.ensure_schema uses the module-level vector client;
        # the isolated test database already has the vector schema above.
        store._schema_ready = True
        with psycopg2.connect(url) as conn, conn.cursor() as cur:
            store._create_schema(cur)
        scope = f"publish-race-{uuid4()}"
        doc_id, version_id, case_id, run_id = (str(uuid4()) for _ in range(4))
        with psycopg2.connect(url) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO knowledge_documents (id, parking_lot_id, file_name, category) "
                "VALUES (%s, %s, 'test.txt', 'regulation')",
                (doc_id, scope),
            )
            cur.execute(
                "INSERT INTO knowledge_document_versions "
                "(id, document_id, version_no, status, file_name) "
                "VALUES (%s, %s, 1, 'TESTED', 'test.txt')",
                (version_id, doc_id),
            )
            cur.execute(
                "INSERT INTO knowledge_test_cases (id, parking_lot_id, question, kind) "
                "VALUES (%s, %s, 'Question?', 'abstain') RETURNING updated_at",
                (case_id, scope),
            )
            suite = suite_fingerprint([{"id": case_id, "updated_at": cur.fetchone()[0].isoformat()}])
            cur.execute(
                "INSERT INTO knowledge_test_runs "
                "(id, parking_lot_id, status, total, done, passed, version_ids, "
                "docs_fingerprint, suite_fingerprint) "
                "VALUES (%s, %s, 'PASSED', 1, 1, 1, %s, %s, %s)",
                (run_id, scope, f'["{version_id}"]', fingerprint([version_id]), suite),
            )
            cur.execute(
                "INSERT INTO knowledge_test_results "
                "(run_id, case_id, question, kind, passed, review_verdict) "
                "VALUES (%s, %s, 'Question?', 'abstain', TRUE, TRUE)",
                (run_id, case_id),
            )

        def validate(latest, ids, cases, review, unpublished):
            reasons = []
            if latest["docs_fingerprint"] != fingerprint(ids):
                reasons.append("document changed")
            if latest["suite_fingerprint"] != suite_fingerprint(cases):
                reasons.append("suite changed")
            if review["rejected"]:
                reasons.append("review rejected")
            if not unpublished:
                reasons.append("no draft")
            return reasons

        writer = psycopg2.connect(url)
        error = []
        started = threading.Event()

        def publish():
            started.set()
            try:
                asyncio.run(store.publish_scope(scope, "admin", validate))
            except Exception as exc:
                error.append(exc)

        try:
            with writer.cursor() as cur:
                cur.execute(
                    "UPDATE knowledge_test_results SET review_verdict = FALSE WHERE run_id = %s",
                    (run_id,),
                )
                thread = threading.Thread(target=publish)
                thread.start()
                self.assertTrue(started.wait(2))
                time.sleep(0.2)
                self.assertTrue(thread.is_alive(), "publish should wait for the review writer")
                writer.commit()
                thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(1, len(error))
                self.assertIsInstance(error[0], KnowledgeGateError)
            with psycopg2.connect(url) as conn, conn.cursor() as cur:
                cur.execute("SELECT status FROM knowledge_document_versions WHERE id = %s", (version_id,))
                self.assertEqual("TESTED", cur.fetchone()[0])
        finally:
            writer.rollback()
            writer.close()
            with psycopg2.connect(url) as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM knowledge_documents WHERE id = %s", (doc_id,))
                cur.execute("DELETE FROM knowledge_test_runs WHERE id = %s", (run_id,))
                cur.execute("DELETE FROM knowledge_test_cases WHERE id = %s", (case_id,))
