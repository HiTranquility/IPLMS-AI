"""Kiểu dữ liệu của domain console; không phụ thuộc transport."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ConsoleActor:
    """Người đang thao tác trên console, với vai trò đọc từ DB ``ai_console``."""

    member_id: str
    roles: frozenset[str]
    session_id: str = ""


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
    # Có khoá TOTP nhưng chưa xác nhận lần nào (vd. admin khẩn cấp tạo bằng CLI).
    totp_secret_set: bool = False


@dataclass(frozen=True)
class ExportedCapture:
    """Một mẫu backend đẩy sang qua A2 (IPLMS ADR-0048 §5) — không có session/user/area rõ."""

    capture_id: str
    image_url: str
    image_sha256: str
    machine_plate: str
    machine_confidence: Optional[float]
    confirmed_plate: str
    human_corrected: bool
    selection_reasons: tuple[str, ...]
    status: str
    purpose: str
    final_plate: str
    group_ref: str
    area_ref: str
    updated_at: str
    captured_at: str
