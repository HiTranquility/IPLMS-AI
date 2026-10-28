#!/usr/bin/env python3
"""Kiểm `app/core/` theo khuôn domain của ADR-0005 (AI_CONVENTIONS §2).

  python -X utf8 script/check_core_layout.py [--core app/core]
Báo: thư mục/file ngoài khuôn trong một domain, file lạ ở gốc `core/`, prompt viết cứng trong `.py`.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT_FILES = {"__init__.py", "constants.py", "enums.py", "exceptions.py"}
DOMAIN_DIRS = {"dtos", "engines", "services", "workflows", "guardrails"}
DOMAIN_FILES = {"__init__.py", "constants.py", "messages.py", "README.md"}
SKIP = {"__pycache__"}

# Prompt viết cứng: chuỗi ba nháy mở đầu bằng lời dặn vai, hoặc hằng *_INSTRUCTIONS / *_PROMPT gán chuỗi.
PROMPT_PATTERNS = (
    re.compile(r'"""\s*(?:Bạn là|Bạn soạn|You are)\b'),
    re.compile(r'^[A-Z_]*(?:INSTRUCTIONS|_PROMPT)\s*(?::[^=]+)?=\s*(?:"""|\(|f?")', re.MULTILINE),
)


def layout_violations(core: Path) -> list[str]:
    out = []
    for entry in sorted(core.iterdir()):
        if entry.name in SKIP:
            continue
        if entry.is_file():
            if entry.name not in ROOT_FILES:
                out.append(f"{entry.as_posix()}: file lạ ở gốc core/ (chỉ {', '.join(sorted(ROOT_FILES))})")
            continue
        for child in sorted(entry.iterdir()):
            if child.name in SKIP:
                continue
            allowed = DOMAIN_DIRS if child.is_dir() else DOMAIN_FILES
            if child.name not in allowed:
                kind = "thư mục" if child.is_dir() else "file"
                out.append(f"{child.as_posix()}: {kind} ngoài khuôn domain (ADR-0005)")
    return out


def prompt_violations(core: Path) -> list[str]:
    out = []
    for path in sorted(core.rglob("*.py")):
        if SKIP & set(path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        lines = {text.count("\n", 0, m.start()) + 1 for p in PROMPT_PATTERNS for m in p.finditer(text)}
        out += [f"{path.as_posix()}:{n}: prompt viết cứng, chuyển ra data/prompts/ (ADR-0005)" for n in sorted(lines)]
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--core", default="app/core")
    args = ap.parse_args()
    core = Path(args.core)
    if not core.is_dir():
        print(f"check_core_layout: không thấy {core}")
        return 2
    found = layout_violations(core) + prompt_violations(core)
    for line in found:
        print(line)
    print(f"check_core_layout: {len(found)} lệch")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
