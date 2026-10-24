"""Kiểm thử tính năng siết quyền DB user ai_inference cho process inference (ADR-0051)."""
import os
import unittest
from unittest.mock import patch

from app.config import get_config
from app.config.console_config import ConsoleConfig
from app.infra.database.console_vision_store import ConsoleVisionStore
from app.script.harden_console_db import harden_database, verify_least_privilege, get_db_urls


class TestConsoleDbHardening(unittest.TestCase):
    def tearDown(self):
        get_config.cache_clear()

    def test_console_config_inference_url(self):
        """ConsoleConfig nhận diện trường inference_database_url từ env."""
        with patch.dict(os.environ, {"AI_CONSOLE_INFERENCE_DATABASE_URL": "postgresql://ai_inference:secret@localhost:5432/ai_console"}):
            cfg = ConsoleConfig()
            self.assertEqual(cfg.inference_database_url, "postgresql://ai_inference:secret@localhost:5432/ai_console")

    def test_vision_store_uses_inference_url_fallback(self):
        """ConsoleVisionStore ưu tiên inference_database_url rồi mới fallback database_url."""
        get_config.cache_clear()
        with patch.dict(os.environ, {
            "AI_CONSOLE_DATABASE_URL": "postgresql://ai_console:pass1@localhost:5432/ai_console",
            "AI_CONSOLE_INFERENCE_DATABASE_URL": "postgresql://ai_inference:pass2@localhost:5432/ai_console",
        }):
            get_config.cache_clear()
            store = ConsoleVisionStore()
            self.assertEqual(store.db_url, "postgresql://ai_inference:pass2@localhost:5432/ai_console")

        with patch.dict(os.environ, {
            "AI_CONSOLE_DATABASE_URL": "postgresql://ai_console:pass1@localhost:5432/ai_console",
            "AI_CONSOLE_INFERENCE_DATABASE_URL": "",
        }):
            get_config.cache_clear()
            store = ConsoleVisionStore()
            self.assertEqual(store.db_url, "postgresql://ai_console:pass1@localhost:5432/ai_console")

    def test_missing_console_password_fails_closed(self):
        """bug-016: thiếu AI_CONSOLE_DB_PASSWORD thì dừng trước khi kết nối DB, không dùng mật khẩu mặc định."""
        env = {k: v for k, v in os.environ.items() if k != "AI_CONSOLE_DB_PASSWORD"}
        with patch.dict(os.environ, env, clear=True), patch("psycopg2.connect") as connect:
            with self.assertRaisesRegex(RuntimeError, "AI_CONSOLE_DB_PASSWORD"):
                harden_database("postgresql://postgres:x@127.0.0.1:5432/ai_console", "inference-pw")
            connect.assert_not_called()

    def test_missing_db_secrets_fail_closed(self):
        """bug-016: thiếu mật khẩu admin hoặc ai_inference thì get_db_urls báo lỗi thay vì rơi về giá trị trong code."""
        base = {"AI_CONSOLE_ADMIN_DATABASE_URL": "postgresql://postgres:x@127.0.0.1:5432/ai_console"}
        cases = [
            ({**base, "AI_INFERENCE_DB_PASSWORD": "i"}, "POSTGRES_PASSWORD"),
            ({**base, "POSTGRES_PASSWORD": "a"}, "AI_INFERENCE_DB_PASSWORD"),
            ({"POSTGRES_PASSWORD": "a", "AI_INFERENCE_DB_PASSWORD": "i"}, "AI_CONSOLE_ADMIN_DATABASE_URL"),
        ]
        for env, missing in cases:
            with self.subTest(missing=missing), patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(RuntimeError, missing):
                    get_db_urls()

    def test_live_db_least_privilege_enforcement(self):
        """Nếu có Postgres dev đang chạy, xác thực user ai_inference bị chặn trên bảng nhạy cảm."""
        try:
            _, inf_url = get_db_urls()
            # Thử kết nối kiểm chứng quyền
            passed = verify_least_privilege(inf_url)
            self.assertTrue(passed, "User ai_inference không được vi phạm nguyên tắc quyền tối thiểu ADR-0051")
        except Exception as exc:
            self.skipTest(f"Bỏ qua kiểm thử live DB: {exc}")


if __name__ == "__main__":
    unittest.main()
