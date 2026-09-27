"""PostgreSQL store cho bộ test Knowledge Base (ISSUE-009): test case, lượt chạy, kết quả.

Cùng database với `knowledge_chunks` (ai-db) để lượt chạy đọc "bản xem trước"
không phải đi qua mạng. psycopg2 đồng bộ, bọc `asyncio.to_thread` như
`pgvector_client`.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from app.config import get_config
from app.core.exceptions import KnowledgeGateError, RagPipelineError
from app.infra.database.pgvector_client import pgvector_client

_RUN_COLUMNS = """
    id::text, parking_lot_id, status, total, done, passed, failed_facts, failed_abstain,
    verdict_reasons, error, version_ids, docs_fingerprint, suite_fingerprint,
    started_by, started_at, finished_at,
    (heartbeat_at < NOW() - make_interval(secs => %(stale)s)) AS is_stale,
    answer_profile_id::text, judge_profile_id::text
"""

_CASE_COLUMNS = """
    id::text, parking_lot_id, question, expected_answer, expected_facts, expected_source,
    kind, created_by, author_id, updated_at
"""


def _iso(value) -> str:
    return value.isoformat() if value else ""


def _run_row(row) -> Dict[str, Any]:
    status = row[2]
    # Nhịp tim quá hạn = replica chạy lượt này đã chết. Không có hook lúc khởi
    # động vì 2 replica: một replica khởi động không được huỷ lượt của replica kia.
    if status == "RUNNING" and row[16]:
        status = "ABORTED"
    return {
        "id": row[0],
        "parking_lot_id": row[1],
        "status": status,
        "total": row[3],
        "done": row[4],
        "passed": row[5],
        "failed_facts": row[6],
        "failed_abstain": row[7],
        "verdict_reasons": row[8] or [],
        "error": row[9] or "",
        "version_ids": row[10] or [],
        "docs_fingerprint": row[11] or "",
        "suite_fingerprint": row[12] or "",
        "started_by": row[13] or "",
        "started_at": _iso(row[14]),
        "finished_at": _iso(row[15]),
        "answer_profile_id": row[17] or "",
        "judge_profile_id": row[18] or "",
    }


def _case_row(row) -> Dict[str, Any]:
    return {
        "id": row[0],
        "parking_lot_id": row[1],
        "question": row[2],
        "expected_answer": row[3],
        "expected_facts": row[4] or [],
        "expected_source": row[5] or "",
        "kind": row[6],
        "created_by": row[7],
        "author_id": row[8] or "",
        "updated_at": _iso(row[9]),
    }


class KnowledgeEvalStore:
    def __init__(self, db_url: str | None = None):
        config = get_config()
        self.db_url = db_url or config.llm.database_url
        self._stale = config.eval.stale_after_seconds
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    # ── plumbing ─────────────────────────────────────────────────────────────
    def _connect(self):
        if not self.db_url:
            raise RagPipelineError("Thiếu AI_DATABASE_URL cho bộ test tri thức.")
        try:
            import psycopg2

            return psycopg2.connect(self.db_url, connect_timeout=5)
        except Exception as exc:
            raise RagPipelineError("Không kết nối được PostgreSQL/pgvector.") from exc

    def _tx(self, work: Callable[[Any], Any]) -> Any:
        connection = self._connect()
        try:
            with connection:
                with connection.cursor() as cursor:
                    return work(cursor)
        except (KnowledgeGateError, RagPipelineError):
            raise
        except Exception as exc:
            raise RagPipelineError("Truy vấn bộ test Knowledge Base thất bại.") from exc
        finally:
            connection.close()

    async def _run(self, work: Callable[[Any], Any]) -> Any:
        await self.ensure_schema()
        return await asyncio.to_thread(self._tx, work)

    @staticmethod
    def _scope_sql(column: str = "parking_lot_id") -> str:
        return f"{column} IS NOT DISTINCT FROM %(scope)s"

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            await pgvector_client.ensure_schema()
            await asyncio.to_thread(self._tx, self._create_schema)
            self._schema_ready = True

    @staticmethod
    def _create_schema(cursor) -> None:
        cursor.execute("SELECT pg_advisory_xact_lock(724101)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_test_cases (
                id UUID PRIMARY KEY,
                parking_lot_id VARCHAR(100),
                question TEXT NOT NULL,
                expected_answer TEXT NOT NULL DEFAULT '',
                expected_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
                expected_source VARCHAR(255) NOT NULL DEFAULT '',
                kind VARCHAR(16) NOT NULL
                    CONSTRAINT ck_knowledge_test_cases_kind
                    CHECK (kind IN ('fact', 'explain', 'abstain')),
                created_by VARCHAR(8) NOT NULL DEFAULT 'user',
                author_id VARCHAR(100),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_test_cases_scope"
            " ON knowledge_test_cases (parking_lot_id)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_test_runs (
                id UUID PRIMARY KEY,
                parking_lot_id VARCHAR(100),
                status VARCHAR(16) NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                done INTEGER NOT NULL DEFAULT 0,
                passed INTEGER NOT NULL DEFAULT 0,
                failed_facts INTEGER NOT NULL DEFAULT 0,
                failed_abstain INTEGER NOT NULL DEFAULT 0,
                verdict_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
                error TEXT NOT NULL DEFAULT '',
                version_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                docs_fingerprint VARCHAR(64) NOT NULL DEFAULT '',
                suite_fingerprint VARCHAR(64) NOT NULL DEFAULT '',
                started_by VARCHAR(100),
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMPTZ,
                answer_profile_id UUID,
                judge_profile_id UUID
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_test_runs_scope"
            " ON knowledge_test_runs (parking_lot_id, started_at DESC)"
        )
        cursor.execute("ALTER TABLE knowledge_test_runs ADD COLUMN IF NOT EXISTS answer_profile_id UUID")
        cursor.execute("ALTER TABLE knowledge_test_runs ADD COLUMN IF NOT EXISTS judge_profile_id UUID")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_test_results (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL REFERENCES knowledge_test_runs(id) ON DELETE CASCADE,
                case_id UUID,
                ordinal INTEGER NOT NULL DEFAULT 0,
                question TEXT NOT NULL,
                kind VARCHAR(16) NOT NULL,
                expected_answer TEXT NOT NULL DEFAULT '',
                expected_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
                expected_source VARCHAR(255) NOT NULL DEFAULT '',
                answer TEXT NOT NULL DEFAULT '',
                sources JSONB NOT NULL DEFAULT '[]'::jsonb,
                passed BOOLEAN NOT NULL,
                reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
                review_verdict BOOLEAN,
                review_note TEXT NOT NULL DEFAULT '',
                reviewed_by VARCHAR(100),
                reviewed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_test_results_run"
            " ON knowledge_test_results (run_id, ordinal)"
        )
        cursor.execute(
            """ALTER TABLE knowledge_test_results
                ADD COLUMN IF NOT EXISTS expected_source VARCHAR(255) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS review_verdict BOOLEAN,
                ADD COLUMN IF NOT EXISTS review_note TEXT NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(100),
                ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ"""
        )

    # ── test cases ───────────────────────────────────────────────────────────
    async def list_cases(self, scope: Optional[str]) -> List[Dict[str, Any]]:
        def work(cur):
            cur.execute(
                f"SELECT {_CASE_COLUMNS} FROM knowledge_test_cases"
                f" WHERE {self._scope_sql()} ORDER BY created_at",
                {"scope": scope},
            )
            return [_case_row(row) for row in cur.fetchall()]

        return await self._run(work)

    async def upsert_case(self, case: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
        def work(cur):
            params = {
                "id": case.get("id") or str(uuid4()),
                "scope": case.get("parking_lot_id"),
                "question": case["question"],
                "expected_answer": case.get("expected_answer", ""),
                "expected_facts": json.dumps(case.get("expected_facts") or [], ensure_ascii=False),
                "expected_source": case.get("expected_source", ""),
                "kind": case["kind"],
                "created_by": case.get("created_by") or "user",
                "author": actor_id,
            }
            # Sửa case của scope khác = không khớp WHERE → không có dòng trả về.
            cur.execute(
                f"""
                INSERT INTO knowledge_test_cases
                    (id, parking_lot_id, question, expected_answer, expected_facts,
                     expected_source, kind, created_by, author_id)
                VALUES (%(id)s, %(scope)s, %(question)s, %(expected_answer)s,
                        %(expected_facts)s::jsonb, %(expected_source)s, %(kind)s,
                        %(created_by)s, %(author)s)
                ON CONFLICT (id) DO UPDATE SET
                    question = EXCLUDED.question,
                    expected_answer = EXCLUDED.expected_answer,
                    expected_facts = EXCLUDED.expected_facts,
                    expected_source = EXCLUDED.expected_source,
                    kind = EXCLUDED.kind,
                    author_id = EXCLUDED.author_id,
                    updated_at = NOW()
                WHERE knowledge_test_cases.parking_lot_id IS NOT DISTINCT FROM %(scope)s
                RETURNING {_CASE_COLUMNS}
                """,
                params,
            )
            row = cur.fetchone()
            if row is None:
                raise KnowledgeGateError("Không tìm thấy test case trong phạm vi này.")
            return _case_row(row)

        return await self._run(work)

    async def delete_case(self, case_id: str, scope: Optional[str]) -> bool:
        def work(cur):
            cur.execute(
                f"DELETE FROM knowledge_test_cases WHERE id = %(id)s AND {self._scope_sql()}",
                {"id": case_id, "scope": scope},
            )
            return cur.rowcount > 0

        return await self._run(work)

    # ── runs ─────────────────────────────────────────────────────────────────
    async def create_run(
        self,
        scope: Optional[str],
        started_by: str,
        total: int,
        version_ids: List[str],
        docs_fingerprint: str,
        suite_fingerprint: str,
        max_concurrent: int,
        answer_profile_id: str | None = None,
        judge_profile_id: str | None = None,
    ) -> Dict[str, Any]:
        """Kiểm trần + tạo lượt chạy trong CÙNG transaction có khoá — 2 cú bấm
        đồng thời không lọt qua kiểm tra cùng lúc."""

        def work(cur):
            cur.execute("SELECT pg_advisory_xact_lock(724102)")
            fresh = "status = 'RUNNING' AND heartbeat_at >= NOW() - make_interval(secs => %(stale)s)"
            cur.execute(
                f"SELECT COUNT(*) FROM knowledge_test_runs WHERE {fresh} AND {self._scope_sql()}",
                {"stale": self._stale, "scope": scope},
            )
            if cur.fetchone()[0]:
                raise KnowledgeGateError("Phạm vi này đang có một lượt chạy test chưa xong.")
            cur.execute(f"SELECT COUNT(*) FROM knowledge_test_runs WHERE {fresh}", {"stale": self._stale})
            if cur.fetchone()[0] >= max_concurrent:
                raise KnowledgeGateError(
                    "Hệ thống đang chạy tối đa số lượt test cho phép. Thử lại sau ít phút."
                )
            cur.execute(
                f"""
                INSERT INTO knowledge_test_runs
                    (id, parking_lot_id, status, total, version_ids,
                     docs_fingerprint, suite_fingerprint, started_by, answer_profile_id, judge_profile_id)
                VALUES (%(id)s, %(scope)s, 'RUNNING', %(total)s, %(versions)s::jsonb,
                        %(docs_fp)s, %(suite_fp)s, %(by)s, %(answer_profile_id)s, %(judge_profile_id)s)
                RETURNING {_RUN_COLUMNS}
                """,
                {
                    "id": str(uuid4()),
                    "scope": scope,
                    "total": total,
                    "versions": json.dumps(version_ids),
                    "docs_fp": docs_fingerprint,
                    "suite_fp": suite_fingerprint,
                    "by": started_by,
                    "answer_profile_id": answer_profile_id,
                    "judge_profile_id": judge_profile_id,
                    "stale": self._stale,
                },
            )
            return _run_row(cur.fetchone())

        return await self._run(work)

    async def add_result(self, run_id: str, ordinal: int, result: Dict[str, Any]) -> None:
        def work(cur):
            cur.execute(
                """
                INSERT INTO knowledge_test_results
                    (run_id, case_id, ordinal, question, kind, expected_answer,
                     expected_facts, expected_source, answer, sources, passed, reasons)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s::jsonb)
                """,
                (
                    run_id,
                    result["case_id"],
                    ordinal,
                    result["question"],
                    result["kind"],
                    result["expected_answer"],
                    json.dumps(result["expected_facts"], ensure_ascii=False),
                    result["expected_source"],
                    result["answer"],
                    json.dumps(result["sources"], ensure_ascii=False),
                    result["passed"],
                    json.dumps(result["reasons"], ensure_ascii=False),
                ),
            )
            # Nhịp tim đi cùng mỗi kết quả: lượt chạy đang sống thì heartbeat mới.
            cur.execute(
                """
                UPDATE knowledge_test_runs
                SET done = done + 1, passed = passed + %s, heartbeat_at = NOW()
                WHERE id = %s
                """,
                (1 if result["passed"] else 0, run_id),
            )

        await self._run(work)

    async def finish_run(
        self,
        run_id: str,
        status: str,
        failed_facts: int = 0,
        failed_abstain: int = 0,
        verdict_reasons: List[str] | None = None,
        error: str = "",
    ) -> None:
        def work(cur):
            cur.execute(
                """
                UPDATE knowledge_test_runs
                SET status = %s, failed_facts = %s, failed_abstain = %s,
                    verdict_reasons = %s::jsonb, error = %s, finished_at = NOW(),
                    heartbeat_at = NOW()
                WHERE id = %s
                """,
                (
                    status,
                    failed_facts,
                    failed_abstain,
                    json.dumps(verdict_reasons or [], ensure_ascii=False),
                    error,
                    run_id,
                ),
            )

        await self._run(work)

    async def get_run(self, run_id: str, scope: Optional[str]) -> Optional[Dict[str, Any]]:
        def work(cur):
            cur.execute(
                f"SELECT {_RUN_COLUMNS} FROM knowledge_test_runs"
                f" WHERE id = %(id)s AND {self._scope_sql()}",
                {"id": run_id, "scope": scope, "stale": self._stale},
            )
            row = cur.fetchone()
            return _run_row(row) if row else None

        return await self._run(work)

    async def list_runs(self, scope: Optional[str], limit: int = 20) -> List[Dict[str, Any]]:
        def work(cur):
            cur.execute(
                f"SELECT {_RUN_COLUMNS} FROM knowledge_test_runs WHERE {self._scope_sql()}"
                " ORDER BY started_at DESC LIMIT %(limit)s",
                {"scope": scope, "stale": self._stale, "limit": limit},
            )
            return [_run_row(row) for row in cur.fetchall()]

        return await self._run(work)

    async def list_results(self, run_id: str) -> List[Dict[str, Any]]:
        def work(cur):
            cur.execute(
                """
                SELECT case_id::text, question, kind, expected_answer, expected_facts,
                       answer, sources, passed, reasons, review_verdict, review_note,
                       reviewed_by, reviewed_at, expected_source
                FROM knowledge_test_results WHERE run_id = %s ORDER BY ordinal
                """,
                (run_id,),
            )
            return [
                {
                    "case_id": row[0] or "",
                    "question": row[1],
                    "kind": row[2],
                    "expected_answer": row[3],
                    "expected_facts": row[4] or [],
                    "answer": row[5],
                    "sources": row[6] or [],
                    "passed": row[7],
                    "reasons": row[8] or [],
                    "reviewed": row[9] is not None,
                    "approved": row[9] is True,
                    "review_note": row[10] or "",
                    "reviewed_by": row[11] or "",
                    "reviewed_at": _iso(row[12]),
                    "expected_source": row[13] or "",
                }
                for row in cur.fetchall()
            ]

        return await self._run(work)

    async def review_result(
        self, run_id: str, case_id: str, scope: Optional[str],
        approved: bool, note: str, reviewer_id: str,
    ) -> Optional[Dict[str, Any]]:
        def work(cur):
            cur.execute(
                f"""UPDATE knowledge_test_results r
                SET review_verdict = %(approved)s, review_note = %(note)s,
                    reviewed_by = %(reviewer)s, reviewed_at = NOW()
                FROM knowledge_test_runs run
                WHERE r.run_id = run.id AND run.id = %(run_id)s
                  AND r.case_id = %(case_id)s
                  AND {self._scope_sql('run.parking_lot_id')}
                  AND run.status <> 'RUNNING'
                RETURNING r.case_id::text, r.question, r.kind, r.expected_answer,
                          r.expected_facts, r.answer, r.sources, r.passed, r.reasons,
                          r.review_verdict, r.review_note, r.reviewed_by, r.reviewed_at,
                          r.expected_source""",
                {"approved": approved, "note": note, "reviewer": reviewer_id,
                 "run_id": run_id, "case_id": case_id, "scope": scope},
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "case_id": row[0], "question": row[1], "kind": row[2],
                "expected_answer": row[3], "expected_facts": row[4] or [],
                "answer": row[5], "sources": row[6] or [], "passed": row[7],
                "reasons": row[8] or [], "reviewed": True,
                "approved": row[9] is True, "review_note": row[10] or "",
                "reviewed_by": row[11] or "", "reviewed_at": _iso(row[12]),
                "expected_source": row[13] or "",
            }

        return await self._run(work)

    async def review_summary(self, run_id: str) -> Dict[str, int]:
        def work(cur):
            cur.execute(
                """SELECT COUNT(*) FILTER (WHERE review_verdict IS NOT NULL),
                          COUNT(*) FILTER (WHERE review_verdict = FALSE)
                   FROM knowledge_test_results WHERE run_id = %s""",
                (run_id,),
            )
            reviewed, rejected = cur.fetchone()
            return {"reviewed": reviewed, "rejected": rejected}

        return await self._run(work)

    async def publish_scope(self, scope: Optional[str], published_by: str, validate) -> int:
        """Check the gate and publish in one transaction while writes are blocked.

        Table locks include every relation that can change the gate decision.
        They also protect against writers that do not participate in advisory locks.
        """
        def work(cur):
            cur.execute(
                "LOCK TABLE knowledge_test_results, knowledge_test_runs, "
                "knowledge_test_cases, knowledge_document_versions, ai_model_profiles "
                "IN SHARE ROW EXCLUSIVE MODE"
            )
            cur.execute(
                "SELECT task, id::text FROM ai_model_profiles "
                "WHERE task IN ('copilot_answer', 'test_judge') AND status = 'ACTIVE'"
            )
            active_profile_ids = dict(cur.fetchall())
            cur.execute(
                f"SELECT {_RUN_COLUMNS} FROM knowledge_test_runs "
                f"WHERE {self._scope_sql()} ORDER BY started_at DESC LIMIT 1",
                {"scope": scope, "stale": self._stale},
            )
            row = cur.fetchone()
            latest = _run_row(row) if row else None
            cur.execute(
                """SELECT DISTINCT ON (v.document_id) v.id::text
                   FROM knowledge_document_versions v
                   JOIN knowledge_documents d ON d.id = v.document_id
                  WHERE v.status <> 'ARCHIVED'
                    AND d.parking_lot_id IS NOT DISTINCT FROM %s
                  ORDER BY v.document_id, v.version_no DESC""",
                (scope,),
            )
            current_ids = sorted(row[0] for row in cur.fetchall())
            cur.execute(
                f"SELECT id::text, updated_at FROM knowledge_test_cases "
                f"WHERE {self._scope_sql()} ORDER BY created_at",
                {"scope": scope},
            )
            cases = [{"id": row[0], "updated_at": _iso(row[1])} for row in cur.fetchall()]
            review = {"reviewed": 0, "rejected": 0}
            unpublished = 0
            if latest:
                cur.execute(
                    """SELECT COUNT(*) FILTER (WHERE review_verdict IS NOT NULL),
                              COUNT(*) FILTER (WHERE review_verdict = FALSE)
                       FROM knowledge_test_results WHERE run_id = %s""",
                    (latest["id"],),
                )
                reviewed, rejected = cur.fetchone()
                review = {"reviewed": reviewed, "rejected": rejected}
                cur.execute(
                    """SELECT COUNT(*) FROM knowledge_document_versions
                        WHERE id = ANY(%s::uuid[]) AND status IN ('DRAFT', 'TESTED')""",
                    (list(latest["version_ids"]),),
                )
                unpublished = int(cur.fetchone()[0])
            reasons = validate(latest, current_ids, cases, review, unpublished, active_profile_ids)
            if reasons:
                raise KnowledgeGateError("Chưa được xuất bản: " + " ".join(reasons))
            cur.execute(
                """SELECT v.id::text, v.document_id::text
                     FROM knowledge_document_versions v
                     JOIN knowledge_documents d ON d.id = v.document_id
                    WHERE v.id = ANY(%s::uuid[])
                      AND v.status IN ('DRAFT', 'TESTED')
                      AND d.parking_lot_id IS NOT DISTINCT FROM %s
                    FOR UPDATE OF v""",
                (list(latest["version_ids"]), scope),
            )
            versions = cur.fetchall()
            if len(versions) != unpublished:
                raise KnowledgeGateError("Phiên bản tài liệu đã thay đổi — chạy lại test.")
            for version_id, document_id in versions:
                cur.execute(
                    "UPDATE knowledge_document_versions SET status = 'ARCHIVED' "
                    "WHERE document_id = %s AND status = 'PUBLISHED'",
                    (document_id,),
                )
                cur.execute(
                    """UPDATE knowledge_document_versions
                          SET status = 'PUBLISHED', published_at = NOW(), published_by = %s
                        WHERE id = %s""",
                    (published_by, version_id),
                )
            return len(versions)

        from app.infra.database.model_policy_store import model_policy_store

        await model_policy_store.ensure_schema()
        return await self._run(work)

    # ── phiên bản (đọc cho cổng xuất bản + sinh câu hỏi) ────────────────────
    async def count_unpublished(self, version_ids: List[str]) -> int:
        def work(cur):
            cur.execute(
                """
                SELECT COUNT(*) FROM knowledge_document_versions
                WHERE id = ANY(%s::uuid[]) AND status IN ('DRAFT', 'TESTED')
                """,
                (list(version_ids),),
            )
            return int(cur.fetchone()[0])

        return await self._run(work)

    async def chunks_for_versions(self, version_ids: List[str], limit: int) -> List[Dict[str, Any]]:
        def work(cur):
            cur.execute(
                """
                SELECT content, source FROM knowledge_chunks
                WHERE version_id = ANY(%s::uuid[])
                ORDER BY source, ordinal
                LIMIT %s
                """,
                (list(version_ids), limit),
            )
            return [{"content": row[0], "source": row[1]} for row in cur.fetchall()]

        return await self._run(work)


knowledge_eval_store = KnowledgeEvalStore()
