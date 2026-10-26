"""bug-029: fallback kết nối DB không được tự tạo database trên Postgres khác, và không lộ mật khẩu ra log."""
import os
import unittest
from unittest.mock import MagicMock, patch

import psycopg2

from app.infra.database import db_connection

URL = "postgresql://ai:pw-secret@database-vector:5432/iplms_knowledge"


class DbFallbackTest(unittest.TestCase):
    def setUp(self):
        db_connection._RESOLVED_URL_CACHE.clear()
        # Cô lập môi trường: cổng map mặc định 5435, không chạy trong container (A-2).
        env = patch.dict(os.environ, {"AI_DB_HOST_PORT": "5435"})
        env.start()
        self.addCleanup(env.stop)
        docker = patch.object(db_connection.os.path, "exists", return_value=False)
        docker.start()
        self.addCleanup(docker.stop)

    def test_ung_vien_fallback_thieu_db_thi_khong_tu_tao(self):
        # Ứng viên 127.0.0.1:5432 — Postgres khác trên máy dev, không phải cổng map của DB AI.
        fallback = next(c for c in db_connection.resolve_db_candidates(URL) if ":5432/" in c and "127.0.0.1" in c)

        def connect(url, **_):
            if url == fallback:
                raise psycopg2.OperationalError('database "iplms_knowledge" does not exist')
            raise psycopg2.OperationalError("connection refused")

        with patch.object(db_connection.psycopg2, "connect", side_effect=connect), \
                patch.object(db_connection, "_ensure_database_exists") as ensure:
            with self.assertRaises(psycopg2.OperationalError):
                db_connection.connect_with_fallback(URL)
        ensure.assert_not_called()

    def test_cong_map_cua_db_ai_thieu_db_thi_van_tu_tao(self):
        conn = MagicMock()
        calls = []

        def connect(url, **_):
            calls.append(url)
            if len(calls) == 1:
                raise psycopg2.OperationalError('database "iplms_knowledge" does not exist')
            return conn

        with patch.object(db_connection.psycopg2, "connect", side_effect=connect), \
                patch.object(db_connection, "_ensure_database_exists", return_value=True) as ensure:
            got, used = db_connection.connect_with_fallback(URL)
        # Ứng viên đầu là cổng map của DB AI (5435) nên được tạo; không bao giờ là 5432 của Postgres khác.
        self.assertEqual(1, ensure.call_count)
        self.assertIn(":5435/", ensure.call_args.args[0])
        self.assertIs(conn, got)
        self.assertIn(":5435/", used)

    def test_luat_duoc_tao_db(self):
        self.assertTrue(db_connection._may_create_database(URL, URL))
        self.assertTrue(db_connection._may_create_database(URL.replace("database-vector:5432", "127.0.0.1:5435"), URL))
        self.assertFalse(db_connection._may_create_database(URL.replace("database-vector:5432", "127.0.0.1:5432"), URL))

    def test_log_fallback_che_mat_khau(self):
        fallback = db_connection.resolve_db_candidates(URL)[1]

        def connect(url, **_):
            if url == fallback:
                return MagicMock()
            raise psycopg2.OperationalError("connection refused")

        with patch.object(db_connection.psycopg2, "connect", side_effect=connect), \
                patch.object(db_connection, "logger") as log:
            db_connection.connect_with_fallback(URL)
        logged = " ".join(str(a) for c in log.warning.call_args_list for a in c.args)
        self.assertIn("***", logged)
        self.assertNotIn("pw-secret", logged)


if __name__ == "__main__":
    unittest.main()
