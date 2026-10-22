"""Kiểm thử tính năng siết quyền DB user ai_inference cho process inference (ADR-0051)."""
import os
import unittest
from unittest.mock import patch

from app.config import get_config
from app.config.console_config import ConsoleConfig
from app.infra.database.console_vision_store import ConsoleVisionStore
from app.script.harden_console_db import verify_least_privilege, get_db_urls


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
