#!/usr/bin/env python3
"""Kiểm `app/core/` theo khuôn domain của ADR-0005 (AI_CONVENTIONS §2).

  python -X utf8 script/check_core_layout.py [--core app/core]
Báo: thư mục/file ngoài khuôn trong một domain, file lạ ở gốc `core/`, prompt viết cứng trong `.py`,
và lệch quy ước đặt tên DTO/service (`dtos/*_dto.py`, `services/<stem>_service.py`).
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

# Prompt viết cứng: chuỗi ba nháy mở đầu bằng lời dẫn vai, hoặc hằng *_INSTRUCTIONS / *_PROMPT gán chuỗi.
PROMPT_PATTERNS = (
    re.compile(r'"""\s*(?:Bạn là|Bạn soạn|You are)\b'),
    re.compile(r'^[A-Z_]*(?:INSTRUCTIONS|_PROMPT)\s*(?::[^=]+)?=\s*(?:"""|\(|f?")', re.MULTILINE),
)
CLASS_DEF_RE = re.compile(r"^class\s+\w+", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+", re.MULTILINE)
DATACLASS_RE = re.compile(r"^@dataclass\b", re.MULTILINE)


def _pascal_case(stem: str) -> str:
    return "".join(part.capitalize() for part in stem.split("_"))


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


def naming_violations(core: Path) -> list[str]:
    out = []
    for domain in sorted(core.iterdir()):
        if not domain.is_dir() or domain.name in SKIP:
            continue
        dtos_dir = domain / "dtos"
        if dtos_dir.is_dir():
            for path in sorted(dtos_dir.glob("*.py")):
                text = path.read_text(encoding="utf-8")
                if path.name == "__init__.py":
                    if CLASS_DEF_RE.search(text):
                        out.append(
                            f"{path.as_posix()}: không khai báo class trực tiếp trong dtos/__init__.py; "
                            "đặt trong dtos/<tên>_dto.py (ADR-0005)"
                        )
                elif not path.stem.endswith("_dto"):
                    out.append(f"{path.as_posix()}: file trong dtos/ phải đặt tên <tên>_dto.py (ADR-0005)")

        services_dir = domain / "services"
        if services_dir.is_dir():
            for path in sorted(services_dir.glob("*.py")):
                text = path.read_text(encoding="utf-8")
                if path.name == "__init__.py":
                    if IMPORT_RE.search(text):
                        out.append(
                            f"{path.as_posix()}: services/__init__.py không re-export (tránh che submodule); "
                            "xuất public API ở <domain>/__init__.py (ADR-0005)"
                        )
                    continue
                if not path.stem.endswith("_service"):
                    out.append(f"{path.as_posix()}: file trong services/ phải đặt tên <stem>_service.py (ADR-0005)")
                    continue
                if DATACLASS_RE.search(text):
                    out.append(f"{path.as_posix()}: không khai báo @dataclass DTO trong services/; chuyển sang dtos/ (ADR-0005)")
                expected_cls = _pascal_case(path.stem)
                if not re.search(rf"^class\s+{expected_cls}\b", text, re.MULTILINE):
                    out.append(f"{path.as_posix()}: thiếu class {expected_cls} khớp tên file {path.name} (ADR-0005)")
                if not re.search(rf"^{path.stem}\s*=\s*{expected_cls}\(", text, re.MULTILINE):
                    out.append(
                        f"{path.as_posix()}: thiếu singleton `{path.stem} = {expected_cls}(...)` khớp tên file (ADR-0005)"
                    )
    routes_dir = core.parent / "api" / "rest" / "routes"
    if routes_dir.is_dir():
        for path in sorted(routes_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            if CLASS_DEF_RE.search(text):
                out.append(
                    f"{path.as_posix()}: không khai báo class trực tiếp trong routes/*_controller.py; "
                    "đặt Pydantic schema trong app/api/rest/schemas/<domain>_schema.py (AI_CONVENTIONS §3)"
                )
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
    found = layout_violations(core) + prompt_violations(core) + naming_violations(core)
    for line in found:
        print(line)
    print(f"check_core_layout: {len(found)} lệch")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
