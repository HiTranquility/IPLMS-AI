"""Lifecycle-safe checkpointer factory for LangGraph workflows."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from app.config import get_config
from app.core.exceptions import WorkflowConfigurationError


@asynccontextmanager
async def open_workflow_checkpointer(
    *,
    backend: str | None = None,
    database_url: str | None = None,
    setup_schema: bool | None = None,
) -> AsyncIterator[Any]:
    config = get_config().workflow
    selected = backend or config.checkpoint_backend

    if selected == "memory":
        try:
            from langgraph.checkpoint.memory import InMemorySaver
        except ImportError as exc:
            raise WorkflowConfigurationError(
                "Thiếu package langgraph cho memory checkpointer."
            ) from exc
        yield InMemorySaver()
        return

    if selected != "postgres":
        raise WorkflowConfigurationError(f"Checkpoint backend không hỗ trợ: {selected}")

    connection_string = (database_url or config.checkpoint_database_url).strip()
    if not connection_string:
        raise WorkflowConfigurationError(
            "AI_WORKFLOW_CHECKPOINT_DATABASE_URL là bắt buộc khi dùng PostgreSQL."
        )

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    except ImportError as exc:
        raise WorkflowConfigurationError(
            "Thiếu langgraph-checkpoint-postgres/psycopg cho PostgreSQL checkpoint."
        ) from exc

    # Strict allowlist avoids reviving arbitrary Python modules from checkpoint bytes.
    serializer = JsonPlusSerializer(allowed_msgpack_modules=None)
    async with AsyncPostgresSaver.from_conn_string(
        connection_string,
        serde=serializer,
    ) as checkpointer:
        should_setup = config.checkpoint_setup_schema if setup_schema is None else setup_schema
        if should_setup:
            await checkpointer.setup()
        yield checkpointer
