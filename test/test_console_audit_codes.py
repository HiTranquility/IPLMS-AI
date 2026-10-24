"""bug-020: từ điển mã hành động của trang Nhật ký (ui) phải phủ mọi mã server ghi vào audit.

Quét literal truyền vào `_audit(...)` / `add_audit(...)` trong mã console rồi so phần trước `:`
với `ui/src/pages/Audit/auditActionCodes.json`. Thêm mã mới ở server mà quên khai ở UI thì đỏ.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_CODES = ROOT / "ui" / "src" / "pages" / "Audit" / "auditActionCodes.json"
SOURCES = [
    ROOT / "app" / "infra" / "database" / "console_store.py",
    ROOT / "app" / "infra" / "database" / "console_vision_store.py",
    *sorted((ROOT / "app" / "core" / "console" / "services").glob("*.py")),
]
# Đối số action là literal thứ nhất (có thể là f-string) sau actor trong _audit(cur, actor, "<mã>"...)
# hoặc add_audit(actor, "<mã>"...).
CALL = re.compile(r"""(?:_audit\(\s*cur\s*,\s*[^,]+,|add_audit\(\s*[^,]+,)\s*f?["']([^"']+)["']""")
# Ở console_vision_store, policy.{decision.lower()} chỉ nhận APPROVED/REJECTED (CHECK constraint).
EXPANSIONS = {"policy.{decision.lower()}": ["policy.approved", "policy.rejected"]}
CATEGORIES = {"rbac", "ml", "auth", "review"}


def server_codes() -> set[str]:
    codes: set[str] = set()
    for path in SOURCES:
        for raw in CALL.findall(path.read_text(encoding="utf-8")):
            for code in EXPANSIONS.get(raw, [raw]):
                codes.add(code.split(":", 1)[0])
    return codes


class AuditActionCodesTest(unittest.TestCase):
    def setUp(self):
        self.ui = json.loads(UI_CODES.read_text(encoding="utf-8"))

    def test_quet_duoc_ma_server(self):
        codes = server_codes()
        self.assertIn("member.invite", codes)
        self.assertIn("snapshot.freeze", codes)
        self.assertTrue(all("{" not in c for c in codes), codes)

    def test_moi_ma_server_co_trong_tu_dien_ui(self):
        missing = sorted(server_codes() - set(self.ui))
        self.assertEqual([], missing, "Thêm các mã này vào auditActionCodes.json và i18n audit.actions")

    def test_moi_ma_ui_thuoc_nhom_bo_loc(self):
        self.assertEqual({}, {k: v for k, v in self.ui.items() if v not in CATEGORIES})


if __name__ == "__main__":
    unittest.main()
