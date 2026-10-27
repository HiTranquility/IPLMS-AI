#!/usr/bin/env python3
"""Regression checks for check_core_layout.py on a throwaway core tree (ADR-0005)."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parent
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location("check_core_layout", TOOLS / "check_core_layout.py")
ccl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccl)


def make(root: Path, files: dict[str, str]) -> None:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


class CheckCoreLayoutTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.core = Path(self.tmp.name) / "core"
        self.addCleanup(self.tmp.cleanup)

    def test_khuon_dung_khong_bao(self):
        make(self.core, {
            "__init__.py": "", "constants.py": "X = 1\n",
            "copilot/__init__.py": "", "copilot/messages.py": 'NO_CONTEXT = "x"\n',
            "copilot/engines/rag/__init__.py": "", "copilot/workflows/dispute/graph.py": "",
            "copilot/guardrails/output_guard.py": "", "vision/constants.py": "MIN = 1\n",
            "vision/__pycache__/x.pyc": "",
        })
        self.assertEqual([], ccl.layout_violations(self.core))
        self.assertEqual([], ccl.prompt_violations(self.core))

    def test_thu_muc_va_file_ngoai_khuon(self):
        make(self.core, {
            "helpers.py": "", "copilot/prompts/__init__.py": "",
            "forecast/readers/r.py": "", "copilot/utils.py": "",
        })
        found = "\n".join(ccl.layout_violations(self.core))
        for name in ("helpers.py", "copilot/prompts", "forecast/readers", "copilot/utils.py"):
            self.assertIn(name, found)

    def test_prompt_viet_cung(self):
        make(self.core, {
            "a/engines/judge.py": 'JUDGE_INSTRUCTIONS = """Chấm điểm."""\n',
            "a/engines/gen.py": 'X = """Bạn là trợ lý."""\n',
            "a/engines/ok.py": '"""Docstring module."""\nSYSTEM_PROMPT = load("x")\n',
        })
        found = ccl.prompt_violations(self.core)
        self.assertEqual(2, len(found), found)
        self.assertTrue(any("judge.py:1" in f for f in found))


if __name__ == "__main__":
    unittest.main()
