"""Nạp prompt có version từ `data/prompts/<tên>/` (ADR-0005).

Mỗi prompt một thư mục: `vN.md` là lời dặn hệ thống (bản số lớn nhất được dùng),
`user.md` là khuôn user message, `schema.json` là JSON schema output (nếu có).
Thiếu file thì báo lỗi ngay, không có prompt dự phòng viết trong code.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.util.logger import logger

_VERSION_FILE = re.compile(r"^v(\d+)\.md$")


def _default_root() -> Path:
    candidates = [
        Path(os.getcwd()) / "data" / "prompts",
        Path(__file__).resolve().parents[3] / "data" / "prompts",
        Path("/app/data/prompts"),
    ]
    return next((p for p in candidates if p.exists()), candidates[0])


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    text: str
    hash: str

    @property
    def label(self) -> str:
        """Nhãn telemetry `<tên>_<version>#<hash8>`; backend đọc qua `promptVersion`, không đổi dạng."""
        return f"{self.name}_{self.version}#{self.hash[:8]}"


class PromptStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _default_root()

    def _dir(self, name: str) -> Path:
        folder = self.root / name
        if not folder.is_dir():
            raise FileNotFoundError(f"Không thấy thư mục prompt {folder}")
        return folder

    @lru_cache(maxsize=None)
    def system(self, name: str) -> Prompt:
        versions = sorted(
            (int(m.group(1)), path)
            for path in self._dir(name).iterdir()
            if (m := _VERSION_FILE.match(path.name))
        )
        if not versions:
            raise FileNotFoundError(f"Prompt '{name}' chưa có file vN.md")
        number, path = versions[-1]
        text = path.read_text(encoding="utf-8").strip()
        prompt = Prompt(name, f"v{number}", text, hashlib.sha256(text.encode("utf-8")).hexdigest())
        logger.info("Đã nạp prompt %s", prompt.label)
        return prompt

    @lru_cache(maxsize=None)
    def user_template(self, name: str) -> str:
        return (self._dir(name) / "user.md").read_text(encoding="utf-8").rstrip("\n")

    @lru_cache(maxsize=None)
    def schema(self, name: str) -> dict[str, Any]:
        return json.loads((self._dir(name) / "schema.json").read_text(encoding="utf-8"))


prompt_store = PromptStore()
