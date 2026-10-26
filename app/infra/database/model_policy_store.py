"""Persist immutable task model profiles in the Copilot PostgreSQL database."""
from __future__ import annotations

import asyncio
from typing import Any, Callable
from uuid import uuid4

from app.config import get_config
from app.infra.database.db_connection import connect_with_fallback
from app.core.exceptions import KnowledgeGateError, RagPipelineError


def _row(row) -> dict[str, Any]:
    return {
        "id": row[0], "task": row[1], "revision": row[2],
        "provider": row[3], "model": row[4], "reasoning_effort": row[5],
        "max_output_tokens": row[6], "timeout_seconds": row[7],
        "status": row[8], "tested_at": row[9].isoformat() if row[9] else "",
        "created_by": row[10] or "", "created_at": row[11].isoformat(),
        "activated_at": row[12].isoformat() if row[12] else "",
        "activated_by": row[13] or "",
    }


_COLUMNS = (
    "id::text, task, revision, provider, model, reasoning_effort, "
    "max_output_tokens, timeout_seconds, status, tested_at, created_by, created_at, "
    "activated_at, activated_by"
)


class ModelPolicyStore:
    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or get_config().llm.database_url
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    def _tx(self, work: Callable[[Any], Any]) -> Any:
        if not self.db_url:
            raise RagPipelineError("Thiếu AI_DATABASE_URL để quản trị model.")
        try:
            connection, self.db_url = connect_with_fallback(self.db_url, connect_timeout=3)
            try:
                with connection:
                    with connection.cursor() as cursor:
                        return work(cursor)
            finally:
                connection.close()
        except (KnowledgeGateError, RagPipelineError, ValueError):
            raise
        except Exception as exc:
            raise RagPipelineError("Không truy cập được hồ sơ model AI.") from exc

    async def _run(self, work: Callable[[Any], Any]) -> Any:
        await self.ensure_schema()
        return await asyncio.to_thread(self._tx, work)

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return

            def create(cur):
                cur.execute("SELECT pg_advisory_xact_lock(724102)")
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS ai_model_profiles (
                        id UUID PRIMARY KEY,
                        task VARCHAR(32) NOT NULL,
                        revision INTEGER NOT NULL,
                        provider VARCHAR(16) NOT NULL,
                        model VARCHAR(120) NOT NULL,
                        reasoning_effort VARCHAR(16) NOT NULL,
                        max_output_tokens INTEGER NOT NULL,
                        timeout_seconds INTEGER NOT NULL,
                        status VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
                        tested_at TIMESTAMPTZ,
                        created_by VARCHAR(100),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        activated_at TIMESTAMPTZ,
                        activated_by VARCHAR(100),
                        CONSTRAINT uq_ai_model_profile_revision UNIQUE (task, revision),
                        CONSTRAINT ck_ai_model_profile_task CHECK
                            (task IN ('copilot_answer', 'test_generation', 'test_judge')),
                        CONSTRAINT ck_ai_model_profile_provider CHECK
                            (provider IN ('openai', 'ollama')),
                        CONSTRAINT ck_ai_model_profile_status CHECK
                            (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED'))
                    )"""
                )
                cur.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_model_profile_active "
                    "ON ai_model_profiles (task) WHERE status = 'ACTIVE'"
                )
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS ai_model_profile_activations (
                        id UUID PRIMARY KEY,
                        profile_id UUID NOT NULL REFERENCES ai_model_profiles(id),
                        task VARCHAR(32) NOT NULL,
                        actor_id VARCHAR(100) NOT NULL,
                        activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )"""
                )

            await asyncio.to_thread(self._tx, create)
            self._schema_ready = True

    async def list_profiles(self) -> list[dict[str, Any]]:
        def work(cur):
            cur.execute(f"SELECT {_COLUMNS} FROM ai_model_profiles ORDER BY task, revision DESC")
            return [_row(row) for row in cur.fetchall()]

        return await self._run(work)

    async def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        def work(cur):
            cur.execute(f"SELECT {_COLUMNS} FROM ai_model_profiles WHERE id = %s", (profile_id,))
            row = cur.fetchone()
            return _row(row) if row else None

        return await self._run(work)

    async def get_active(self, task: str) -> dict[str, Any] | None:
        def work(cur):
            cur.execute(
                f"SELECT {_COLUMNS} FROM ai_model_profiles WHERE task = %s AND status = 'ACTIVE'",
                (task,),
            )
            row = cur.fetchone()
            return _row(row) if row else None

        return await self._run(work)

    async def create_profile(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        def work(cur):
            cur.execute("SELECT pg_advisory_xact_lock(724103)")
            cur.execute(
                "SELECT COALESCE(MAX(revision), 0) + 1 FROM ai_model_profiles WHERE task = %s",
                (values["task"],),
            )
            revision = cur.fetchone()[0]
            profile_id = str(uuid4())
            cur.execute(
                f"""INSERT INTO ai_model_profiles
                    (id, task, revision, provider, model, reasoning_effort,
                     max_output_tokens, timeout_seconds, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING {_COLUMNS}""",
                (
                    profile_id, values["task"], revision, values["provider"],
                    values["model"], values["reasoning_effort"],
                    values["max_output_tokens"], values["timeout_seconds"], actor,
                ),
            )
            return _row(cur.fetchone())

        return await self._run(work)

    async def mark_tested(self, profile_id: str) -> dict[str, Any]:
        def work(cur):
            cur.execute(
                f"""UPDATE ai_model_profiles SET tested_at = NOW()
                    WHERE id = %s AND status = 'DRAFT' RETURNING {_COLUMNS}""",
                (profile_id,),
            )
            row = cur.fetchone()
            if not row:
                raise KnowledgeGateError("Chỉ có thể thử hồ sơ đang ở trạng thái nháp.")
            return _row(row)

        return await self._run(work)

    async def activate(self, profile_id: str, actor: str, validate=None) -> dict[str, Any]:
        def work(cur):
            if validate:
                cur.execute(
                    "LOCK TABLE knowledge_test_results, knowledge_test_runs, "
                    "knowledge_test_cases, knowledge_document_versions "
                    "IN SHARE ROW EXCLUSIVE MODE"
                )
            cur.execute("LOCK TABLE ai_model_profiles IN SHARE ROW EXCLUSIVE MODE")
            cur.execute(
                f"SELECT {_COLUMNS} FROM ai_model_profiles WHERE id = %s FOR UPDATE",
                (profile_id,),
            )
            row = cur.fetchone()
            if not row:
                raise KnowledgeGateError("Không tìm thấy hồ sơ model.")
            profile = _row(row)
            if not profile["tested_at"]:
                raise KnowledgeGateError("Hồ sơ chưa thử kết nối thành công.")
            if profile["status"] == "ACTIVE":
                return profile
            if validate:
                cur.execute(
                    """SELECT id::text, status, total, docs_fingerprint,
                              suite_fingerprint, answer_profile_id::text,
                              judge_profile_id::text
                       FROM knowledge_test_runs WHERE parking_lot_id IS NULL
                       ORDER BY started_at DESC LIMIT 1"""
                )
                run = cur.fetchone()
                cur.execute(
                    """SELECT DISTINCT ON (v.document_id) v.id::text
                       FROM knowledge_document_versions v
                       JOIN knowledge_documents d ON d.id = v.document_id
                      WHERE v.status <> 'ARCHIVED' AND d.parking_lot_id IS NULL
                      ORDER BY v.document_id, v.version_no DESC"""
                )
                versions = [row[0] for row in cur.fetchall()]
                cur.execute(
                    "SELECT id::text, updated_at FROM knowledge_test_cases "
                    "WHERE parking_lot_id IS NULL"
                )
                cases = [{"id": row[0], "updated_at": row[1].isoformat()}
                         for row in cur.fetchall()]
                reviewed = rejected = 0
                if run:
                    cur.execute(
                        """SELECT COUNT(*) FILTER (WHERE review_verdict IS NOT NULL),
                                  COUNT(*) FILTER (WHERE review_verdict = FALSE)
                           FROM knowledge_test_results WHERE run_id = %s""",
                        (run[0],),
                    )
                    reviewed, rejected = cur.fetchone()
                cur.execute(
                    "SELECT id::text FROM ai_model_profiles "
                    "WHERE task = 'test_judge' AND status = 'ACTIVE'"
                )
                judge = cur.fetchone()
                reasons = validate(profile, run, versions, cases, reviewed, rejected,
                                   judge[0] if judge else "")
                if reasons:
                    raise KnowledgeGateError("Chưa thể kích hoạt: " + " ".join(reasons))
            cur.execute(
                "UPDATE ai_model_profiles SET status = 'ARCHIVED' "
                "WHERE task = %s AND status = 'ACTIVE'",
                (profile["task"],),
            )
            cur.execute(
                f"""UPDATE ai_model_profiles SET status = 'ACTIVE',
                    activated_at = NOW(), activated_by = %s
                    WHERE id = %s RETURNING {_COLUMNS}""",
                (actor, profile_id),
            )
            active = _row(cur.fetchone())
            cur.execute(
                "INSERT INTO ai_model_profile_activations (id, profile_id, task, actor_id) "
                "VALUES (%s, %s, %s, %s)",
                (str(uuid4()), profile_id, profile["task"], actor),
            )
            return active

        return await self._run(work)


model_policy_store = ModelPolicyStore()
