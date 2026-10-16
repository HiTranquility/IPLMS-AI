"""Kiểu dữ liệu của domain console; không phụ thuộc transport."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ConsoleActor:
    """Người đang thao tác trên console, với vai trò đọc từ DB ``ai_console``."""

    member_id: str
    roles: frozenset[str]
