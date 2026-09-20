"""Lifecycle-safe checkpointer factory for LangGraph workflows."""
from __future__ import annotations

from contextlib import asynccontextmanager
import re
from typing import Any, AsyncIterator

from app.config import get_config
from app.core.exceptions import WorkflowConfigurationError


_SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def validate_checkpoint_schema(schema: str) -> str:
    normalized = schema.strip()
    if not _SCHEMA_PATTERN.fullmatch(normalized):
        raise WorkflowConfigurationError(
            "AI_WORKFLOW_CHECKPOINT_SCHEMA chỉ nhận chữ thường, số, dấu gạch dưới "
            "và phải bắt đầu bằng chữ hoặc dấu gạch dưới."
        )
    return normalized


def build_checkpoint_connection_string(database_url: str, schema: str) -> str:
    """Scope an existing PostgreSQL DSN to the validated checkpoint schema."""
    try:
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
    except ImportError as exc:
        raise WorkflowConfigurationError("Thiếu psycopg cho PostgreSQL checkpoint.") from exc

    validated_schema = validate_checkpoint_schema(schema)
    try:
        connection_options = conninfo_to_dict(database_url)
        existing_options = str(connection_options.pop("options", "")).strip()
        search_path_option = f"-csearch_path={validated_schema}"
        connection_options["options"] = " ".join(
            option for option in (existing_options, search_path_option) if option
        )
        return make_conninfo(**connection_options)
    except Exception as exc:
        raise WorkflowConfigurationError(
            "AI_WORKFLOW_CHECKPOINT_DATABASE_URL không phải PostgreSQL DSN hợp lệ."
        ) from exc


async def _ensure_checkpoint_schema(database_url: str, schema: str) -> None:
    try:
        from psycopg import AsyncConnection, sql
    except ImportError as exc:
        raise WorkflowConfigurationError("Thiếu psycopg cho PostgreSQL checkpoint.") from exc

    try:
        async with await AsyncConnection.connect(database_url, autocommit=True) as connection:
            await connection.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
            )
    except Exception as exc:
        raise WorkflowConfigurationError(
            "Không thể tạo PostgreSQL schema cho workflow checkpoint."
        ) from exc


@asynccontextmanager
async def open_workflow_checkpointer(
    *,
    backend: str | None = None,
    database_url: str | None = None,
    schema: str | None = None,
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

    selected_schema = validate_checkpoint_schema(schema or config.checkpoint_schema)
    should_setup = config.checkpoint_setup_schema if setup_schema is None else setup_schema
    if should_setup:
        await _ensure_checkpoint_schema(connection_string, selected_schema)
    scoped_connection_string = build_checkpoint_connection_string(
        connection_string,
        selected_schema,
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
        scoped_connection_string,
        serde=serializer,
    ) as checkpointer:
        if should_setup:
            await checkpointer.setup()
        yield checkpointer
