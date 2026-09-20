"""Operational checks and bounded retention for workflow checkpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.config import get_config
from app.core.exceptions import WorkflowConfigurationError
from app.infra.workflow.checkpointer import (
    build_checkpoint_connection_string,
    open_workflow_checkpointer,
    validate_checkpoint_schema,
)


def _resolve_settings(
    database_url: str | None,
    schema: str | None,
) -> tuple[str, str, str]:
    config = get_config().workflow
    resolved_url = (database_url or config.checkpoint_database_url).strip()
    if not resolved_url:
        raise WorkflowConfigurationError(
            "AI_WORKFLOW_CHECKPOINT_DATABASE_URL là bắt buộc cho thao tác checkpoint."
        )
    resolved_schema = validate_checkpoint_schema(schema or config.checkpoint_schema)
    return (
        resolved_url,
        resolved_schema,
        build_checkpoint_connection_string(resolved_url, resolved_schema),
    )


async def _connect(scoped_connection_string: str) -> Any:
    try:
        from psycopg import AsyncConnection
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise WorkflowConfigurationError("Thiếu psycopg cho PostgreSQL checkpoint.") from exc
    try:
        return await AsyncConnection.connect(
            scoped_connection_string,
            autocommit=True,
            row_factory=dict_row,
        )
    except Exception as exc:
        raise WorkflowConfigurationError(
            "Không thể kết nối PostgreSQL workflow checkpoint."
        ) from exc


async def inspect_checkpoint_store(
    *,
    database_url: str | None = None,
    schema: str | None = None,
) -> dict[str, Any]:
    """Return metadata-only readiness without exposing DSN or checkpoint payloads."""
    _url, resolved_schema, scoped_url = _resolve_settings(database_url, schema)
    async with await _connect(scoped_url) as connection:
        row = await (
            await connection.execute(
                """
                SELECT
                    current_schema() AS current_schema,
                    to_regclass('checkpoint_migrations') IS NOT NULL AS has_migrations,
                    to_regclass('checkpoints') IS NOT NULL AS has_checkpoints,
                    to_regclass('checkpoint_blobs') IS NOT NULL AS has_blobs,
                    to_regclass('checkpoint_writes') IS NOT NULL AS has_writes
                """
            )
        ).fetchone()
        assert row is not None
        tables = {
            "checkpoint_migrations": bool(row["has_migrations"]),
            "checkpoints": bool(row["has_checkpoints"]),
            "checkpoint_blobs": bool(row["has_blobs"]),
            "checkpoint_writes": bool(row["has_writes"]),
        }
        migration_version: int | None = None
        thread_count: int | None = None
        if tables["checkpoint_migrations"]:
            migration_row = await (
                await connection.execute(
                    "SELECT MAX(v) AS version FROM checkpoint_migrations"
                )
            ).fetchone()
            migration_version = migration_row["version"] if migration_row else None
        if tables["checkpoints"]:
            count_row = await (
                await connection.execute(
                    "SELECT COUNT(DISTINCT thread_id) AS count FROM checkpoints"
                )
            ).fetchone()
            thread_count = int(count_row["count"]) if count_row else 0

    return {
        "ready": row["current_schema"] == resolved_schema and all(tables.values()),
        "schema": resolved_schema,
        "active_schema": row["current_schema"],
        "tables": tables,
        "migration_version": migration_version,
        "thread_count": thread_count,
    }


async def _expired_threads(
    scoped_url: str,
    *,
    retention_days: int,
    batch_size: int,
) -> list[dict[str, Any]]:
    try:
        async with await _connect(scoped_url) as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT
                        thread_id,
                        MAX((checkpoint->>'ts')::timestamptz) AS last_checkpoint_at
                    FROM checkpoints
                    WHERE checkpoint ? 'ts'
                    GROUP BY thread_id
                    HAVING MAX((checkpoint->>'ts')::timestamptz)
                        < NOW() - make_interval(days => %s)
                    ORDER BY last_checkpoint_at ASC, thread_id ASC
                    LIMIT %s
                    """,
                    (retention_days, batch_size),
                )
            ).fetchall()
        return list(rows)
    except WorkflowConfigurationError:
        raise
    except Exception as exc:
        raise WorkflowConfigurationError(
            "Không thể đọc checkpoint quá hạn; hãy chạy lệnh setup/check trước."
        ) from exc


async def prune_expired_checkpoint_threads(
    *,
    database_url: str | None = None,
    schema: str | None = None,
    retention_days: int | None = None,
    batch_size: int | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """List or delete one bounded batch of expired workflow threads."""
    config = get_config().workflow
    resolved_url, resolved_schema, scoped_url = _resolve_settings(database_url, schema)
    days = (
        config.checkpoint_retention_days
        if retention_days is None
        else retention_days
    )
    limit = (
        config.checkpoint_retention_batch_size
        if batch_size is None
        else batch_size
    )
    if days < 1:
        raise WorkflowConfigurationError("retention_days phải lớn hơn hoặc bằng 1.")
    if not 1 <= limit <= 1000:
        raise WorkflowConfigurationError("batch_size phải nằm trong khoảng 1..1000.")

    candidates = await _expired_threads(
        scoped_url,
        retention_days=days,
        batch_size=limit,
    )
    if apply and candidates:
        async with open_workflow_checkpointer(
            backend="postgres",
            database_url=resolved_url,
            schema=resolved_schema,
            setup_schema=False,
        ) as checkpointer:
            for candidate in candidates:
                await checkpointer.adelete_thread(str(candidate["thread_id"]))

    def safe_timestamp(value: Any) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value) if value is not None else None

    timestamps = [candidate.get("last_checkpoint_at") for candidate in candidates]

    return {
        "applied": apply,
        "schema": resolved_schema,
        "retention_days": days,
        "batch_size": limit,
        "matched": len(candidates),
        "deleted": len(candidates) if apply else 0,
        "candidate_window": {
            "oldest_checkpoint_at": safe_timestamp(timestamps[0]) if timestamps else None,
            "newest_checkpoint_at": safe_timestamp(timestamps[-1]) if timestamps else None,
        },
    }
