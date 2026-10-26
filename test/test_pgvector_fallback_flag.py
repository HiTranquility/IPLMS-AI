"""ai ADR-0001: thiếu pgvector chỉ chạy chế độ mảng khi bật AI_EMBEDDING_ALLOW_NO_PGVECTOR."""
import unittest
from unittest.mock import MagicMock, patch

from app.core.exceptions import RagPipelineError
from app.infra.database.pgvector_client import PgVectorClient


def _connection_without_pgvector():
    cursor = MagicMock()
    cursor.fetchone.return_value = None  # pg_available_extensions không có 'vector'
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    return connection, cursor


class PgVectorFallbackFlagTest(unittest.TestCase):
    def _client(self, allow: bool) -> PgVectorClient:
        client = PgVectorClient("postgresql://test/ai")
        client.allow_no_pgvector = allow
        return client

    def test_missing_pgvector_is_refused_by_default(self):
        client = self._client(allow=False)
        connection, cursor = _connection_without_pgvector()
        with patch.object(client, "_connect_sync", return_value=connection):
            with self.assertRaisesRegex(RagPipelineError, "AI_EMBEDDING_ALLOW_NO_PGVECTOR"):
                client._ensure_schema_sync()
        executed = " ".join(str(call.args[0]) for call in cursor.execute.call_args_list)
        self.assertNotIn("iplms_cosine_sim", executed)
        self.assertNotIn("CREATE TABLE", executed)

    def test_flag_enables_array_fallback(self):
        client = self._client(allow=True)
        connection, cursor = _connection_without_pgvector()
        with patch.object(client, "_connect_sync", return_value=connection):
            client._ensure_schema_sync()
        executed = " ".join(str(call.args[0]) for call in cursor.execute.call_args_list)
        self.assertIn("iplms_cosine_sim", executed)
        self.assertIn("DOUBLE PRECISION[]", executed)
        self.assertFalse(client._has_pgvector)

    def test_flag_defaults_off(self):
        from app.config.embedding_config import EmbeddingConfig

        self.assertFalse(EmbeddingConfig.model_fields["allow_no_pgvector"].default)


if __name__ == "__main__":
    unittest.main()
