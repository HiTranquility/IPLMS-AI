"""Telemetry mỗi request AI trong `database-vector` (IPLMS ADR-0049, đề Final §4.2/§6.6).

Lưu câu hỏi/câu trả lời ĐÃ CHE PII và user dạng HMAC. Bản ghi quá
`AI_TELEMETRY_RETENTION_DAYS` bị xoá (tối đa mỗi giờ một lần, khi có ghi mới).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from app.config import get_config
from app.infra.database.db_connection import connect_with_fallback
from app.core.exceptions import RagPipelineError

_PURGE_EVERY_SECONDS = 3600


class AiRequestLogStore:
    def __init__(self, db_url: str | None = None, retention_days: int | None = None) -> None:
        self.db_url = db_url if db_url is not None else get_config().llm.database_url
        self.retention_days = retention_days or get_config().telemetry.retention_days
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()
        self._last_purge = 0.0

    def _tx(self, work: Callable[[Any], Any]) -> Any:
        if not self.db_url:
            raise RagPipelineError("Thiếu AI_DATABASE_URL để lưu telemetry AI.")
        try:
            connection, self.db_url = connect_with_fallback(self.db_url, connect_timeout=3)
            try:
                with connection:
                    with connection.cursor() as cursor:
                        return work(cursor)
            finally:
                connection.close()
        except (RagPipelineError, ValueError):
            raise
        except Exception as exc:
            raise RagPipelineError("Không truy cập được telemetry AI.") from exc

    async def _run(self, work: Callable[[Any], Any]) -> Any:
        await self.ensure_schema()
        return await asyncio.to_thread(self._tx, work)

    @staticmethod
    def _create_schema(cur) -> None:
        cur.execute("SELECT pg_advisory_xact_lock(724301)")
        cur.execute(
            """CREATE TABLE IF NOT EXISTS ai_request_log (
                turn_id UUID PRIMARY KEY,
                at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                task VARCHAR(32) NOT NULL,
                status VARCHAR(16) NOT NULL,
                model VARCHAR(120) NOT NULL DEFAULT '',
                model_revision VARCHAR(64) NOT NULL DEFAULT '',
                prompt_version VARCHAR(64) NOT NULL DEFAULT '',
                tools TEXT[] NOT NULL DEFAULT '{}',
                input_tokens INTEGER,
                output_tokens INTEGER,
                latency_ms INTEGER NOT NULL,
                cost_usd NUMERIC(12, 6),
                user_hash CHAR(64),
                user_role VARCHAR(16),
                parking_lot_id VARCHAR(128),
                query_redacted TEXT NOT NULL,
                answer_redacted TEXT,
                error_code VARCHAR(64),
                feedback SMALLINT,
                feedback_at TIMESTAMPTZ,
                CONSTRAINT ck_ai_request_log_status CHECK
                    (status IN ('SUCCESS', 'REFUSED', 'NO_CONTEXT', 'ERROR')),
                CONSTRAINT ck_ai_request_log_feedback CHECK (feedback IN (-1, 1))
            )"""
        )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_ai_request_log_at ON ai_request_log (at)")

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            await asyncio.to_thread(self._tx, self._create_schema)
            self._schema_ready = True

    async def record(self, entry: dict[str, Any]) -> None:
        purge = time.monotonic() - self._last_purge > _PURGE_EVERY_SECONDS
        retention = self.retention_days

        def work(cur):
            cur.execute(
                """INSERT INTO ai_request_log
                   (turn_id, task, status, model, model_revision, prompt_version, tools,
                    input_tokens, output_tokens, latency_ms, cost_usd, user_hash, user_role,
                    parking_lot_id, query_redacted, answer_redacted, error_code)
                   VALUES (%(turn_id)s, %(task)s, %(status)s, %(model)s, %(model_revision)s,
                           %(prompt_version)s, %(tools)s, %(input_tokens)s, %(output_tokens)s,
                           %(latency_ms)s, %(cost_usd)s, %(user_hash)s, %(user_role)s,
                           %(parking_lot_id)s, %(query_redacted)s, %(answer_redacted)s,
                           %(error_code)s)""",
                entry,
            )
            if purge:
                cur.execute(
                    "DELETE FROM ai_request_log WHERE at < NOW() - make_interval(days => %s)",
                    (retention,),
                )

        await self._run(work)
        if purge:
            self._last_purge = time.monotonic()

    async def set_feedback(self, turn_id: str, user_hash: str, rating: int) -> bool:
        def work(cur):
            cur.execute(
                """UPDATE ai_request_log SET feedback = %s, feedback_at = NOW()
                   WHERE turn_id = %s AND user_hash = %s
                     AND at >= NOW() - make_interval(days => %s)
                   RETURNING turn_id""",
                (rating, turn_id, user_hash, self.retention_days),
            )
            return cur.fetchone() is not None

        return await self._run(work)

    async def summary(self, days: int) -> dict[str, Any]:
        def work(cur):
            # Chỉ lượt của người dùng sản phẩm; lượt thử trong console (`console_try`) không tính
            # vào dashboard mức dùng (IPLMS ADR-0050 §3).
            window = "at >= NOW() - make_interval(days => %s) AND task IN ('copilot_ask', 'copilot_stream')"
            cur.execute(
                f"""SELECT COUNT(*),
                       COUNT(*) FILTER (WHERE status = 'SUCCESS'),
                       COUNT(*) FILTER (WHERE status = 'REFUSED'),
                       COUNT(*) FILTER (WHERE status = 'NO_CONTEXT'),
                       COUNT(*) FILTER (WHERE status = 'ERROR'),
                       COALESCE(AVG(latency_ms), 0),
                       COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms), 0),
                       COALESCE(SUM(input_tokens), 0),
                       COALESCE(SUM(output_tokens), 0),
                       COUNT(*) FILTER (WHERE cost_usd IS NULL),
                       COALESCE(SUM(cost_usd), 0),
                       COUNT(*) FILTER (WHERE feedback = 1),
                       COUNT(*) FILTER (WHERE feedback = -1)
                   FROM ai_request_log WHERE {window}""",
                (days,),
            )
            row = cur.fetchone()
            cur.execute(
                f"""SELECT (at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS day, COUNT(*),
                           COUNT(*) FILTER (WHERE status = 'ERROR'),
                           COUNT(*) FILTER (WHERE status = 'REFUSED'),
                           AVG(latency_ms),
                           COALESCE(SUM(output_tokens), 0)
                    FROM ai_request_log WHERE {window}
                    GROUP BY day ORDER BY day""",
                (days,),
            )
            series = cur.fetchall()
            total = int(row[0])
            cost_known = total > 0 and int(row[9]) == 0
            total_cost = float(row[10]) if cost_known else 0.0
            avg_lat = round(float(row[5]), 1)
            total_out = int(row[8])
            avg_speed = round(total_out / (avg_lat * total / 1000.0), 1) if (total > 0 and avg_lat > 0) else 0.0
            return {
                "window_days": days,
                "total_requests": total,
                "success_requests": int(row[1]),
                "refused_requests": int(row[2]),
                "no_context_requests": int(row[3]),
                "error_requests": int(row[4]),
                "avg_latency_ms": avg_lat,
                "p95_latency_ms": round(float(row[6]), 1),
                "avg_speed_tok_s": avg_speed,
                "input_tokens": int(row[7]),
                "output_tokens": total_out,
                "cost_known": cost_known,
                "total_cost_usd": round(total_cost, 6),
                "avg_cost_usd": round(total_cost / total, 6) if cost_known else 0.0,
                "thumbs_up": int(row[11]),
                "thumbs_down": int(row[12]),
                "days": [
                    {
                        "date": d.isoformat(),
                        "requests": int(n),
                        "errors": int(e),
                        "refused": int(r),
                        "avg_latency_ms": round(float(lat or 0), 1),
                        "speed_tok_s": round(float(out_tok or 0) / (float(lat or 1) * int(n) / 1000.0), 1) if (int(n) > 0 and float(lat or 0) > 0) else 0.0,
                    }
                    for d, n, e, r, lat, out_tok in series
                ],
            }

        return await self._run(work)

    async def list_recent(
        self, limit: int, status: str | None = None, feedback: int | None = None,
        before: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lượt gần nhất cho Copilot Lab — chỉ cột đã che PII, không trả `user_hash`."""
        def work(cur):
            where, params = ["TRUE"], []
            if status:
                where.append("status = %s")
                params.append(status)
            if feedback is not None:
                where.append("feedback = %s")
                params.append(feedback)
            if before:
                where.append("at < %s::timestamptz")
                params.append(before)
            cur.execute(
                f"""SELECT turn_id::text, at, task, status, model, prompt_version,
                           input_tokens, output_tokens, latency_ms, cost_usd, user_role,
                           parking_lot_id, query_redacted, answer_redacted, error_code, feedback
                    FROM ai_request_log WHERE {' AND '.join(where)}
                    ORDER BY at DESC, turn_id LIMIT %s""",
                (*params, limit),
            )
            return [
                {
                    "turn_id": r[0], "at": r[1].isoformat(), "task": r[2], "status": r[3],
                    "model": r[4], "prompt_version": r[5], "input_tokens": r[6],
                    "output_tokens": r[7], "latency_ms": int(r[8]),
                    "speed_tok_s": round(float(r[7]) / (float(r[8]) / 1000.0), 1) if (r[7] and r[8] and r[8] > 0) else None,
                    "cost_usd": float(r[9]) if r[9] is not None else None,
                    "user_role": r[10] or "", "parking_lot_id": r[11] or "",
                    "query": r[12], "answer": r[13] or "", "error_code": r[14] or "",
                    "feedback": r[15],
                }
                for r in cur.fetchall()
            ]

        return await self._run(work)

    async def turn_time(self, turn_id: str):
        """Thời điểm của một lượt còn trong hạn lưu; None nếu không có."""
        def work(cur):
            cur.execute("SELECT at FROM ai_request_log WHERE turn_id = %s", (turn_id,))
            row = cur.fetchone()
            return row[0] if row else None

        return await self._run(work)


ai_request_log_store = AiRequestLogStore()
