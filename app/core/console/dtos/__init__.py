"""Kiểu dữ liệu của domain console; không phụ thuộc transport."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ConsoleActor:
    """Người đang thao tác trên console, với vai trò đọc từ DB ``ai_console``."""

    member_id: str
    roles: frozenset[str]


@dataclass(frozen=True)
class ConsoleSession:
    """Phiên đăng nhập đã kiểm hạn; ``mfa_done`` False nghĩa là mới qua bước 1."""

    session_id: str
    actor: ConsoleActor
    email: str
    display_name: str
    mfa_done: bool
    totp_enabled: bool
    step_up_at: Optional[datetime]
