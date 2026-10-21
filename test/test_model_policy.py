"""Focused validation and adapter tests for Admin model profiles."""
import asyncio
import os
from urllib.parse import urlencode
from uuid import uuid4
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.model_policy.engines.validation import clean_profile
from app.core.model_policy.services.model_policy_service import ModelPolicyService
from app.infra.llm.llm_factory import LlmFactory
from app.infra.database.model_policy_store import ModelPolicyStore
from app.core.exceptions import KnowledgeGateError
from app.core.knowledge_eval.engines.gate import fingerprint, suite_fingerprint
from app.api.grpc.mappers.model_policy_mapper import to_model_profile_response


def profile(task="copilot_answer", provider="openai", effort="low"):
    return {
        "id": "profile-1", "task": task, "revision": 2,
        "provider": provider, "model": "test-model", "reasoning_effort": effort,
        "max_output_tokens": 700, "timeout_seconds": 20, "status": "DRAFT",
    }


class ProfileValidationTest(unittest.TestCase):
    def test_grpc_profile_response_contains_revision_and_no_secret(self):
        record = {
            **profile(), "tested_at": "", "created_by": "admin",
            "created_at": "2026-09-27T00:00:00+00:00", "activated_at": "", "activated_by": "",
        }
        message = to_model_profile_response(record)
        self.assertEqual(2, message.revision)
        self.assertEqual("test-model", message.model)
        self.assertNotIn("api_key", message.DESCRIPTOR.fields_by_name)

    def test_rejects_unsupported_provider_and_ollama_reasoning(self):
        with self.assertRaises(ValueError):
            clean_profile({**profile(), "provider": "arbitrary-provider"})
        with self.assertRaises(ValueError):
            clean_profile(profile(provider="ollama"))

    def test_rejects_model_id_as_url(self):
        with self.assertRaises(ValueError):
            clean_profile({**profile(), "model": "https://example.com/path?key=secret"})

    def test_openai_reasoning_is_sent_with_profile_limits(self):
        fake = SimpleNamespace(responses=SimpleNamespace(
            create=AsyncMock(return_value=SimpleNamespace(output_text="IPLMS"))
        ))
        llm = LlmFactory(client=fake, profile=profile())
        asyncio.run(llm.generate_response("system", "question", "context"))
        request = fake.responses.create.await_args.kwargs
        self.assertEqual("test-model", request["model"])
        self.assertEqual({"effort": "low"}, request["reasoning"])
        self.assertEqual(700, request["max_output_tokens"])
        self.assertFalse(request["store"])
        self.assertEqual("copilot_answer:2", llm.profile_revision)

    def test_active_revision_is_resolved_for_each_request(self):
        llm = LlmFactory(client=object())
        with patch("app.infra.database.model_policy_store.model_policy_store") as store:
            store.db_url = "configured"
            store.get_active = AsyncMock(return_value=profile())
            selected = asyncio.run(llm.for_task("copilot_answer"))
        self.assertEqual("test-model", selected.model)
        self.assertEqual("profile-1", selected.profile_id)


class ProbeTest(unittest.TestCase):
    def test_answer_profile_requires_grounded_probe_before_marking_tested(self):
        store = SimpleNamespace(
            get_profile=AsyncMock(return_value=profile()),
            mark_tested=AsyncMock(return_value=profile()),
        )
        service = ModelPolicyService(store)
        with patch("app.core.model_policy.services.model_policy_service.get_config") as config, \
             patch("app.core.model_policy.services.model_policy_service.LlmFactory") as factory:
            config.return_value.llm.llm_api_key = "test-only"
            factory.return_value.generate_response = AsyncMock(return_value="Không biết")
            with self.assertRaisesRegex(Exception, "ngữ cảnh"):
                asyncio.run(service.test_profile("profile-1"))
        store.mark_tested.assert_not_awaited()


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class ModelPolicyDatabaseTest(unittest.TestCase):
    def test_answer_activation_requires_reviewed_candidate_suite(self):
        import psycopg2
        from psycopg2 import sql
        from app.infra.database.knowledge_eval_store import KnowledgeEvalStore
        from app.infra.database.pgvector_client import PgVectorClient

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        schema = "model_policy_test_" + uuid4().hex
        admin = psycopg2.connect(base_url)
        try:
            with admin, admin.cursor() as cur:
                cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            url = base_url + ("&" if "?" in base_url else "?") + urlencode({"options": "-csearch_path=" + schema + ",public"})
            vector = PgVectorClient(url)
            asyncio.run(vector.ensure_schema())
            with psycopg2.connect(url) as conn, conn.cursor() as cur:
                KnowledgeEvalStore._create_schema(cur)
            store = ModelPolicyStore(url)
            candidate = asyncio.run(store.create_profile(clean_profile(profile()), "admin-test"))
            asyncio.run(store.mark_tested(candidate["id"]))
            doc_id, version_id, run_id = (str(uuid4()) for _ in range(3))
            cases = []
            with psycopg2.connect(url) as conn, conn.cursor() as cur:
                cur.execute("INSERT INTO knowledge_documents (id, file_name, category) VALUES (%s, 'test.txt', 'regulation')", (doc_id,))
                cur.execute(
                    "INSERT INTO knowledge_document_versions (id, document_id, version_no, status, file_name) "
                    "VALUES (%s, %s, 1, 'PUBLISHED', 'test.txt')",
                    (version_id, doc_id),
                )
                for index in range(5):
                    case_id = str(uuid4())
                    cur.execute(
                        "INSERT INTO knowledge_test_cases (id, question, kind) "
                        "VALUES (%s, %s, 'abstain') RETURNING updated_at",
                        (case_id, f"Question {index}"),
                    )
                    cases.append({"id": case_id, "updated_at": cur.fetchone()[0].isoformat()})
                cur.execute(
                    """INSERT INTO knowledge_test_runs
                       (id, status, total, done, passed, version_ids, docs_fingerprint,
                        suite_fingerprint, answer_profile_id)
                       VALUES (%s, 'PASSED', 5, 5, 5, %s::jsonb, %s, %s, %s)""",
                    (run_id, f'["{version_id}"]', fingerprint([version_id]),
                     suite_fingerprint(cases), candidate["id"]),
                )
                for index, case in enumerate(cases):
                    cur.execute(
                        "INSERT INTO knowledge_test_results "
                        "(run_id, case_id, ordinal, question, kind, passed, review_verdict) "
                        "VALUES (%s, %s, %s, %s, 'abstain', TRUE, %s)",
                        (run_id, case["id"], index, f"Question {index}", index != 0),
                    )
            service = ModelPolicyService(store)
            with patch("app.core.model_policy.services.model_policy_service.knowledge_eval_store") as eval_store:
                eval_store.ensure_schema = AsyncMock()
                with self.assertRaisesRegex(KnowledgeGateError, "duyệt OK"):
                    asyncio.run(service.activate(candidate["id"], "admin-test"))
                with psycopg2.connect(url) as conn, conn.cursor() as cur:
                    cur.execute("UPDATE knowledge_test_results SET review_verdict = TRUE WHERE run_id = %s", (run_id,))
                active = asyncio.run(service.activate(candidate["id"], "admin-test"))
            self.assertEqual("ACTIVE", active["status"])
            self.assertEqual(candidate["id"], asyncio.run(store.get_active("copilot_answer"))["id"])
        finally:
            with admin, admin.cursor() as cur:
                cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            admin.close()

    def test_activation_and_rollback_are_atomic_across_revisions(self):
        import psycopg2
        from psycopg2 import sql

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        schema = "model_policy_test_" + uuid4().hex
        admin = psycopg2.connect(base_url)
        try:
            with admin, admin.cursor() as cur:
                cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            url = base_url + ("&" if "?" in base_url else "?") + urlencode({"options": "-csearch_path=" + schema})
            store = ModelPolicyStore(url)
            values = clean_profile({**profile(task="test_generation"), "reasoning_effort": "none"})
            first = asyncio.run(store.create_profile(values, "admin-1"))
            asyncio.run(store.mark_tested(first["id"]))
            asyncio.run(store.activate(first["id"], "admin-1"))
            second = asyncio.run(store.create_profile({**values, "model": "test-model-2"}, "admin-2"))
            asyncio.run(store.mark_tested(second["id"]))
            asyncio.run(store.activate(second["id"], "admin-2"))
            self.assertEqual("ARCHIVED", asyncio.run(store.get_profile(first["id"]))["status"])
            asyncio.run(store.activate(first["id"], "admin-3"))
            active = asyncio.run(store.get_active("test_generation"))
            self.assertEqual(first["id"], active["id"])
            self.assertEqual("admin-3", active["activated_by"])
            with psycopg2.connect(url) as conn, conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM ai_model_profile_activations")
                self.assertEqual(3, cur.fetchone()[0])
        finally:
            with admin, admin.cursor() as cur:
                cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            admin.close()

    def test_draft_probe_and_activation_gate_are_persisted(self):
        import psycopg2
        from app.infra.database.knowledge_eval_store import KnowledgeEvalStore
        from app.infra.database.pgvector_client import PgVectorClient

        url = os.environ["AI_TEST_DATABASE_URL"]
        asyncio.run(PgVectorClient(url).ensure_schema())
        eval_store = KnowledgeEvalStore(url)
        with psycopg2.connect(url) as conn, conn.cursor() as cur:
            eval_store._create_schema(cur)
        store = ModelPolicyStore(url)
        created = asyncio.run(store.create_profile(clean_profile(profile()), "admin-test"))
        try:
            self.assertEqual("DRAFT", created["status"])
            self.assertEqual(created["id"], asyncio.run(store.get_profile(created["id"]))["id"])
            tested = asyncio.run(store.mark_tested(created["id"]))
            self.assertTrue(tested["tested_at"])
            with self.assertRaises(KnowledgeGateError):
                asyncio.run(store.activate(created["id"], "admin-test", lambda *_: ["suite missing"]))
            self.assertEqual("DRAFT", asyncio.run(store.get_profile(created["id"]))["status"])
        finally:
            with psycopg2.connect(url) as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM ai_model_profiles WHERE id = %s", (created["id"],))
