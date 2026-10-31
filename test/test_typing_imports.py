"""Tên trong `typing` dùng ở module nào phải được import ở chính module đó (bug-048).

Merge giải conflict từng xoá `from typing import List` khỏi `server_config.py` trong khi
annotation vẫn dùng `List` → `NameError` lúc import `app.config`, service không khởi động.
Test đọc AST nên chạy được cả khi chưa cài dependency.
"""
import ast
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
TYPING_NAMES = {"Any", "Dict", "List", "Optional", "Tuple", "Set", "Union", "Iterable", "Callable"}


def _bound_names(tree: ast.AST) -> set[str]:
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            bound.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
    return bound


def missing_typing_imports(source: str) -> set[str]:
    tree = ast.parse(source)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return (used & TYPING_NAMES) - _bound_names(tree)


class TypingImportsTest(unittest.TestCase):
    def test_detects_missing_import(self):
        self.assertEqual(missing_typing_imports("def f() -> List[str]:\n    return []\n"), {"List"})
        self.assertEqual(missing_typing_imports("from typing import List\nx: List[int] = []\n"), set())

    def test_every_app_module_imports_typing_names_it_uses(self):
        offenders = {}
        for path in sorted(APP_DIR.rglob("*.py")):
            missing = missing_typing_imports(path.read_text(encoding="utf-8"))
            if missing:
                offenders[str(path.relative_to(APP_DIR.parent))] = sorted(missing)
        self.assertEqual(offenders, {})


if __name__ == "__main__":
    unittest.main()
