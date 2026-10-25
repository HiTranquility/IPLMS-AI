#!/usr/bin/env python3
"""Regression checks for board_gen.py and check_generated.py on a throwaway docs tree (ADR-0060)."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bg = load("board_gen")
cg = load("check_generated")

BUG = """# 🐛 {code}: {title}

> intro

| | |
|---|---|
| **Trạng thái** | {status} |
{extra}
## Hành vi
"""
ISSUE = """# 🏷️ {code}: [Chore] {title}

## 🎯 Goal

## 📌 Meta

| | |
|---|---|
| **Trạng thái** | {status} |
{extra}
## ✅ Tasks
{tasks}"""


class BoardGenTest(unittest.TestCase):
    def setUp(self):
        sandbox = tempfile.TemporaryDirectory(prefix="board-gen-")
        self.addCleanup(sandbox.cleanup)
        self.root = Path(sandbox.name)
        self.saved = (bg.ROOT, bg.DOCS, bg.PROJ, bg.OUT)
        self.addCleanup(lambda: setattr(bg, "OUT", self.saved[3]) or setattr(bg, "PROJ", self.saved[2])
                        or setattr(bg, "DOCS", self.saved[1]) or setattr(bg, "ROOT", self.saved[0]))
        bg.ROOT, bg.DOCS = self.root, self.root / "docs"
        bg.PROJ = bg.DOCS / "projects"
        bg.OUT = bg.PROJ / "BOARD.md"

    def bug(self, code, status, extra="", title="t"):
        p = bg.PROJ / "bugs" / f"{code}-x" / "bug.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(BUG.format(code=code, title=title, status=status, extra=extra), encoding="utf-8")
        return p

    def issue(self, code, status, extra="", tasks="", folder="issues"):
        p = bg.PROJ / folder / "10-2026" / f"{code}-x" / "issue.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(ISSUE.format(code=code, title="i", status=status, extra=extra, tasks=tasks), encoding="utf-8")
        return p

    def section(self, text, emoji):
        out, on = [], False
        for line in text.splitlines():
            if line.startswith("## "):
                on = line.startswith(f"## {emoji}")
                continue
            if on and line.startswith("| ") and "](" in line:
                out.append(line)
        return out

    def test_sections_follow_status_and_owner(self):
        self.bug("bug-001", "🆕 New", "| **Ưu tiên** | 🔴 |")
        self.bug("bug-002", "📝 Draft", "| **Người nhận** | Khoa |\n| **Hạn** | 2026-11-01 |")
        self.bug("bug-003", "🚧 In Progress — đang sửa")
        self.bug("bug-004", "👀 Review — chờ PR")
        self.bug("bug-005", "⛔ Bị chặn bởi bug-001")
        self.bug("bug-006", "✅ Fixed — còn E2E", "| **Ngày đóng** | 2026-10-20 |")
        self.bug("bug-007", "⛔ Cancelled")
        self.bug("bug-008", "✅ Fixed trong nhánh tích hợp — chưa merge")
        text = bg.render()
        self.assertIn("bug-008", "".join(self.section(text, "⏳")))  # ✅ mà chưa merge vẫn chờ duyệt
        self.assertIn("bug-001", "".join(self.section(text, "🙋")))
        self.assertIn("| Khoa | 2026-11-01 |", "".join(self.section(text, "🗓️")))
        self.assertIn("bug-003", "".join(self.section(text, "🚧")))
        self.assertIn("bug-004", "".join(self.section(text, "⏳")))
        self.assertIn("bug-005", "".join(self.section(text, "⛔")))
        self.assertIn("bug-006", "".join(self.section(text, "✅")))
        self.assertNotIn("bug-007", text)  # đóng mà không có Ngày đóng thì không lên ✅

    def test_task_table_rows_and_closed_parent(self):
        tasks = ("## 📋 Việc trên BOARD\n\n| Việc | Người nhận | Hạn | Ưu tiên | Trạng thái |\n|---|---|---|---|---|\n"
                 "| Đo ANPR | Khoa | 2026-10-17 | 🟠 | 🚧 Đang làm |\n| Review M2 | — | — | 🟢 | 🆕 |\n"
                 "\n### Phạm vi\n\n| Người | Phạm vi |\n|---|---|\n| Khoa | ANPR |\n")  # bảng thứ hai không thành dòng BOARD
        self.issue("ISSUE-001", "🚧 In Progress", tasks=tasks)
        text = bg.render()
        self.assertIn("| Đo ANPR | [ISSUE-001]", "".join(self.section(text, "🚧")))
        self.assertIn("| Review M2 | [ISSUE-001]", "".join(self.section(text, "🙋")))
        self.assertEqual(1, text.count("| Đo ANPR |"))
        self.assertNotIn("| Khoa | [ISSUE-001]", text)
        self.assertNotIn("| ANPR |", text)
        self.issue("ISSUE-001", "✅ Done", "| **Ngày đóng** | 2026-10-25 |", tasks=tasks)
        text = bg.render()
        self.assertEqual([], self.section(text, "🚧") + self.section(text, "🙋"))
        self.assertEqual(2, len(self.section(text, "✅")))

    def test_opt_in_types_need_owner_or_tasks(self):
        prob = bg.DOCS / "problems" / "10-2026" / "PROB-050-x.md"
        prob.parent.mkdir(parents=True)
        prob.write_text(BUG.format(code="PROB-050", title="p", status="💡 Proposed", extra=""), encoding="utf-8")
        self.assertNotIn("PROB-050", bg.render())
        prob.write_text(BUG.format(code="PROB-050", title="p", status="💡 Proposed", extra="| **Người nhận** | Phát |"),
                        encoding="utf-8")
        self.assertIn("[PROB-050](../problems/10-2026/PROB-050-x.md)", bg.render())

    def test_done_section_sorted_and_limited(self):
        for i in range(bg.DONE_LIMIT + 3):
            self.bug(f"bug-{i + 100:03d}", "✅ Fixed", f"| **Ngày đóng** | 2026-09-{i + 1:02d} |")
        rows = self.section(bg.render(), "✅")
        self.assertEqual(bg.DONE_LIMIT, len(rows))
        self.assertIn("2026-09-23", rows[0])

    def test_output_is_stable_and_ignores_crlf(self):
        p = self.bug("bug-001", "🚧 In Progress", "| **Người nhận** | A |")
        first = bg.render()
        self.assertEqual(first, bg.render())
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(first, bg.render())
        bg.OUT.write_text(first, encoding="utf-8", newline="\n")
        self.assertEqual(first, bg.render())  # tiêu đề lấy lại từ bản đã sinh

    def test_check_mode(self):
        self.bug("bug-001", "🚧 In Progress")
        bg.OUT.parent.mkdir(parents=True, exist_ok=True)
        bg.OUT.write_text("# 📋 BOARD — x\n", encoding="utf-8")
        argv = sys.argv
        self.addCleanup(lambda: setattr(sys, "argv", argv))
        sys.argv = ["board_gen.py", "--check"]
        self.assertEqual(1, bg.main())
        bg.OUT.write_text(bg.render(), encoding="utf-8", newline="\n")
        self.assertEqual(0, bg.main())

    def test_done_rule_matches_check_drift(self):
        if not (TOOLS / "check_drift.py").exists():
            self.skipTest("repo con không có check_drift.py")
        drift = load("check_drift")
        for s in ("✅ Done", "✅ Fixed — còn E2E", "🚧 In Progress — Phase 1 ✅", "⛔ Cancelled", "Done cho dev; còn gates",
                  "🔄 REVIEWING", "Resolved", "🆕 New"):
            self.assertEqual(drift.is_done(s), bg.is_done(s), s)


class CheckGeneratedTest(unittest.TestCase):
    def test_board_and_registry_blocked_in_feature_pr(self):
        files = ["docs/projects/BOARD.md", "docs/projects/issue-registry.md", "script/x.py"]
        self.assertEqual(files[:2], cg.violations(files, "feature/ISSUE-133-2026-10-x"))

    def test_monthly_chore_may_regenerate_registry_only(self):
        files = ["docs/projects/BOARD.md", "docs/projects/issue-registry.md"]
        self.assertEqual(["docs/projects/BOARD.md"],
                         cg.violations(files, "chore/CHORE-001-2026-10-monthly-maintenance"))

    def test_clean_pr_passes(self):
        self.assertEqual([], cg.violations(["docs/projects/bugs/bug-001-x/bug.md"], "bugfix/bug-001-2026-10-x"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
