import tempfile
import unittest
from pathlib import Path

from app.infra.llm.llm_factory import _user_message
from app.infra.llm.prompts import PromptStore


class PromptStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_lay_ban_so_lon_nhat_va_nhan_telemetry(self):
        self._write("p/v2.md", "hai\n")
        self._write("p/v10.md", "mười\n")
        prompt = PromptStore(self.root).system("p")
        self.assertEqual(("v10", "mười"), (prompt.version, prompt.text))
        self.assertRegex(prompt.label, r"^p_v10#[0-9a-f]{8}$")

    def test_thieu_file_thi_bao_loi_khong_dung_du_phong(self):
        self._write("p/user.md", "x")
        with self.assertRaises(FileNotFoundError):
            PromptStore(self.root).system("p")
        with self.assertRaises(FileNotFoundError):
            PromptStore(self.root).system("khong-co")

    def test_khuon_user_message_copilot(self):
        message = _user_message("Phí {ô tô}?", "[1] [Nguồn: a.pdf]\nPhí 25.000đ")
        self.assertTrue(message.startswith("CÂU HỎI CỦA NGƯỜI DÙNG:\nPhí {ô tô}?\n\n"))
        self.assertTrue(message.endswith("NGỮ CẢNH ĐÃ TRUY XUẤT TỪ KHO TRI THỨC:\n[1] [Nguồn: a.pdf]\nPhí 25.000đ"))


if __name__ == "__main__":
    unittest.main()
