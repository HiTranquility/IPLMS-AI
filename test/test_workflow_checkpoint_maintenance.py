import argparse
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import io
import unittest
from unittest.mock import AsyncMock, patch

from psycopg.conninfo import conninfo_to_dict
from pydantic import ValidationError

from app.config.workflow_config import WorkflowConfig
from app.core.exceptions import WorkflowConfigurationError
from app.infra.workflow.checkpointer import (
    build_checkpoint_connection_string,
    validate_checkpoint_schema,
)
from app.infra.workflow.maintenance import prune_expired_checkpoint_threads
from app.script.manage_workflow_checkpoints import run


class CheckpointConnectionTest(unittest.TestCase):
    def test_scopes_connection_to_validated_schema_and_preserves_options(self):
        connection_string = build_checkpoint_connection_string(
            "postgresql://worker:secret@localhost/iplms?options=-cstatement_timeout%3D5000",
            "ai_workflow",
        )
        parsed = conninfo_to_dict(connection_string)
        self.assertIn("-cstatement_timeout=5000", parsed["options"])
        self.assertIn("-csearch_path=ai_workflow", parsed["options"])

    def test_rejects_schema_name_that_could_change_search_path(self):
        for schema in ("public,evil", "AI_WORKFLOW", "bad-name", "1workflow"):
            with self.subTest(schema=schema):
                with self.assertRaises(WorkflowConfigurationError):
                    validate_checkpoint_schema(schema)

    def test_retention_config_rejects_unbounded_values(self):
        with self.assertRaises(ValidationError):
            WorkflowConfig(checkpoint_retention_days=0)
        with self.assertRaises(ValidationError):
            WorkflowConfig(checkpoint_retention_batch_size=1001)


class CheckpointRetentionTest(unittest.IsolatedAsyncioTestCase):
    async def test_prune_is_dry_run_by_default_and_omits_thread_id(self):
        expired = AsyncMock(
            return_value=[
                {
                    "thread_id": "tenant-sensitive-workflow-id",
                    "last_checkpoint_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
                }
            ]
        )
        with patch(
            "app.infra.workflow.maintenance._expired_threads",
            expired,
        ):
            report = await prune_expired_checkpoint_threads(
                database_url="postgresql://worker:secret@localhost/iplms",
                retention_days=30,
                batch_size=10,
            )

        self.assertFalse(report["applied"])
        self.assertEqual(report["matched"], 1)
        self.assertEqual(report["deleted"], 0)
        self.assertNotIn("tenant-sensitive-workflow-id", str(report))
        self.assertEqual(
            report["candidate_window"]["oldest_checkpoint_at"],
            "2026-08-01T00:00:00+00:00",
        )

    async def test_apply_deletes_only_returned_bounded_candidates(self):
        candidates = [
            {"thread_id": "workflow-1", "last_checkpoint_at": None},
            {"thread_id": "workflow-2", "last_checkpoint_at": None},
        ]
        saver = AsyncMock()

        @asynccontextmanager
        async def fake_open(**_kwargs):
            yield saver

        with (
            patch(
                "app.infra.workflow.maintenance._expired_threads",
                AsyncMock(return_value=candidates),
            ),
            patch(
                "app.infra.workflow.maintenance.open_workflow_checkpointer",
                fake_open,
            ),
        ):
            report = await prune_expired_checkpoint_threads(
                database_url="postgresql://worker:secret@localhost/iplms",
                retention_days=30,
                batch_size=2,
                apply=True,
            )

        self.assertEqual(report["deleted"], 2)
        self.assertEqual(
            [call.args[0] for call in saver.adelete_thread.await_args_list],
            ["workflow-1", "workflow-2"],
        )

    async def test_rejects_invalid_manual_retention_limits(self):
        with self.assertRaisesRegex(WorkflowConfigurationError, "retention_days"):
            await prune_expired_checkpoint_threads(
                database_url="postgresql://worker:secret@localhost/iplms",
                retention_days=0,
            )
        with self.assertRaisesRegex(WorkflowConfigurationError, "batch_size"):
            await prune_expired_checkpoint_threads(
                database_url="postgresql://worker:secret@localhost/iplms",
                batch_size=1001,
            )


class CheckpointCliTest(unittest.IsolatedAsyncioTestCase):
    async def test_cli_reports_safe_configuration_error(self):
        args = argparse.Namespace(command="check")
        with (
            patch(
                "app.script.manage_workflow_checkpoints.inspect_checkpoint_store",
                AsyncMock(
                    side_effect=WorkflowConfigurationError(
                        "AI_WORKFLOW_CHECKPOINT_DATABASE_URL là bắt buộc."
                    )
                ),
            ),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            exit_code = await run(args)

        self.assertEqual(exit_code, 1)
        self.assertIn('"ok": false', stdout.getvalue())
        self.assertNotIn("secret", stdout.getvalue())

    async def test_cli_redacts_unexpected_database_error(self):
        args = argparse.Namespace(command="check")
        with (
            patch(
                "app.script.manage_workflow_checkpoints.inspect_checkpoint_store",
                AsyncMock(
                    side_effect=RuntimeError(
                        "postgresql://worker:secret@production.internal/iplms"
                    )
                ),
            ),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            exit_code = await run(args)

        self.assertEqual(exit_code, 1)
        self.assertNotIn("secret", stdout.getvalue())
        self.assertNotIn("production.internal", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
