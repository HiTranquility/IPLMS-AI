"""Focused stdlib tests: run python -B -m unittest discover -s script -p test_branch_policy.py."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from check_branch_policy import creation_month, safe_path, validate


class BranchPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.config = {"namespace": "IPLMS-AI", "legacy_branches": ["khoa-develop"]}
        self.path = "docs/projects/issues/10-2026/ISSUE-013-example/issue.md"
        path = self.repo / self.path
        path.parent.mkdir(parents=True)
        path.write_text("| **Ngày tạo** | 2026-10-13 |\n", encoding="utf-8")
        self.branch = "feature/ISSUE-013-2026-10-example"

    def pr(self, owner="IPLMS-AI", record="ISSUE-013", path=None, created="2026-10-13"):
        return {"title": "fix: " + record, "body": (
            f"Policy-Record: {owner} {record}\nPolicy-Path: {path or self.path}\nPolicy-Created: {created}")}

    def test_local_pr_and_push(self):
        for pr in (None, self.pr()):
            self.assertTrue(validate(self.repo, self.config, self.branch, pr).startswith("VERIFIED_LOCAL"))

    def test_codex_same_rules(self):
        self.assertTrue(validate(self.repo, self.config, self.branch.replace("feature/", "codex/"), self.pr()).startswith("VERIFIED_LOCAL"))

    def test_invalid_grammar_and_month(self):
        for branch in ("codex/arbitrary", "feature/ISSUE-013-example", "feature/ISSUE-013-2026-13-example",
                       "feature/ISSUE-013-0000-10-example", self.branch + "--bad", self.branch + "/bad"):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                validate(self.repo, self.config, branch, self.pr())

    def test_creation_month_must_match(self):
        with self.assertRaises(ValueError):
            validate(self.repo, self.config, self.branch.replace("2026-10", "2026-09"), self.pr())

    def test_missing_local_record_fails_pr_but_push_is_pending(self):
        branch = self.branch.replace("013", "014")
        with self.assertRaises(ValueError):
            validate(self.repo, self.config, branch, self.pr(record="ISSUE-014", path=self.path.replace("013", "014")))
        self.assertTrue(validate(self.repo, self.config, branch).startswith("EXTERNAL_PENDING_PR"))

    def test_namespace_mismatch_and_local_prob(self):
        for pr in (self.pr(owner="IPLMS-Backend"), self.pr(owner="IPLMS-AI", record="PROB-013", path="docs/problems/10-2026/PROB-013-example.md")):
            with self.assertRaises(ValueError):
                validate(self.repo, self.config, self.branch.replace("ISSUE", "PROB") if "PROB" in pr["title"] else self.branch, pr)

    def test_external_declaration_honestly_unverified(self):
        self.assertTrue(validate(self.repo, self.config, self.branch, self.pr(owner="IPLMS")).startswith("EXTERNAL_UNVERIFIED"))
        with self.assertRaises(ValueError):
            validate(self.repo, self.config, self.branch, self.pr(owner="IPLMS", path=self.path.replace("10-2026", "09-2026")))

    def test_metadata_missing_duplicate_title_and_impossible_date(self):
        for pr in ({"title": "missing", "body": ""}, {**self.pr(), "body": self.pr()["body"] + "\nPolicy-Path: duplicate"},
                   self.pr(created="2026-10-99"), self.pr(created="20261013")):
            with self.assertRaises(ValueError):
                validate(self.repo, self.config, self.branch, pr)

    def test_exact_legacy_only(self):
        self.assertTrue(validate(self.repo, self.config, "khoa-develop", {"title": "fix bug-003"}).startswith("LEGACY"))
        with self.assertRaises(ValueError):
            validate(self.repo, self.config, "khoa-develop-extra", {"title": "fix bug-003"})

    def test_exempt_names_still_require_pr_title_record(self):
        for branch in ("main", "develop", "dependabot/pip/update", "khoa-develop"):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                validate(self.repo, self.config, branch, {"title": "no record"})
            validate(self.repo, self.config, branch, {"title": "fix bug-003"})

    def test_review_and_phase_are_not_primary_records(self):
        for name in ("review.md", "phase-1.md", "child/bug.md"):
            relative = "docs/projects/bugs/bug-013-example/" + name
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("| Ngày tạo | 2026-10-13 |", encoding="utf-8")
            with self.subTest(path=relative), self.assertRaises(ValueError):
                validate(self.repo, self.config, "bugfix/bug-013-2026-10-example", self.pr(record="bug-013", path=relative))
        primary = self.repo / "docs/projects/bugs/bug-013-example/bug.md"
        primary.write_text("| Ngày tạo | 2026-09-13 |", encoding="utf-8")
        with self.assertRaises(ValueError):
            validate(self.repo, self.config, "bugfix/bug-013-2026-10-example", self.pr(record="bug-013", path=primary.relative_to(self.repo).as_posix()))

    def test_flat_primary_record(self):
        relative = "docs/problems/10-2026/PROB-013-example.md"
        path = self.repo / relative
        path.parent.mkdir(parents=True)
        path.write_text("| Ngày mở | 2026-10-13 |", encoding="utf-8")
        config = {**self.config, "namespace": "IPLMS"}
        self.assertTrue(validate(self.repo, config, "codex/PROB-013-2026-10-example", self.pr(owner="IPLMS", record="PROB-013", path=relative)).startswith("VERIFIED_LOCAL"))

    def test_reporter_then_creation_date_metadata(self):
        path = self.repo / self.path
        path.write_text("| **Người báo / Ngày** | Codex / 2026-10-15 |", encoding="utf-8")
        self.assertTrue(validate(self.repo, self.config, self.branch, self.pr(created="2026-10-15")).startswith("VERIFIED_LOCAL"))

    def test_traversal_wrong_folder_secret_path(self):
        for path in ("../.env", "docs/projects/bugs/ISSUE-013.md", "/docs/projects/issues/ISSUE-013.md",
                     "docs/projects/issues/SecretKeys/ISSUE-013.md", "docs/projects/issues/x-backup-y/ISSUE-013.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_path(path, "ISSUE-013")

    def test_ambiguous_or_unknown_original_date(self):
        path = self.repo / "unknown.md"
        for text in ("no metadata", "| Ngày kết thúc | 2026-10-01 |", "| Ngày tạo | 2026-09-01 |\n| Created | 2026-10-01 |"):
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                creation_month(path)

    def test_untrusted_title_body_never_executed_or_logged(self):
        marker = self.repo / "executed"
        evil = f"$(touch {marker}); `touch {marker}`"
        pr = self.pr()
        pr["title"] += " " + evil
        pr["body"] += "\n" + evil
        with patch("subprocess.run", side_effect=AssertionError("must never invoke shell")):
            self.assertTrue(validate(self.repo, self.config, self.branch, pr).startswith("VERIFIED_LOCAL"))
        self.assertFalse(marker.exists())

    def test_actual_cli_consumes_event_file_without_shell(self):
        script_dir = self.repo / "script"
        script_dir.mkdir()
        source = Path(__file__).with_name("check_branch_policy.py")
        (script_dir / source.name).write_bytes(source.read_bytes())
        (script_dir / "branch_policy.json").write_text(json.dumps(self.config), encoding="utf-8")
        pr = self.pr()
        pr["head"] = {"ref": self.branch}
        event = self.repo / "event.json"
        event.write_text(json.dumps({"pull_request": pr}), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(script_dir / source.name)],
                                env={**os.environ, "GITHUB_EVENT_PATH": str(event)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VERIFIED_LOCAL", result.stdout)


if __name__ == "__main__":
    unittest.main()
