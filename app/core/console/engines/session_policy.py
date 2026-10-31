"""Luật thuần về hạn phiên console (ADR-0048 §4) — không đọc giờ hệ thống, không I/O."""
from datetime import datetime, timedelta

from app.core.exceptions import ConsoleAuthError


def check_session(
    session: dict, now: datetime, ttl: timedelta, idle: timedelta, require_mfa: bool = True
) -> None:
    """Ném ConsoleAuthError với mã cụ thể; UI dựa vào mã để chuyển đúng màn hình."""
    if session["revoked_at"] is not None:
        raise ConsoleAuthError("Phiên đã đăng xuất.", "SESSION_REVOKED")
    if session["member_status"] == "DISABLED":
        raise ConsoleAuthError("Tài khoản console đã bị khoá.", "MEMBER_DISABLED")
    if now - session["created_at"] > ttl:
        raise ConsoleAuthError("Phiên đã hết hạn, hãy đăng nhập lại.", "SESSION_EXPIRED")
    if now - session["last_seen_at"] > idle:
        raise ConsoleAuthError("Phiên đã rảnh quá lâu, hãy đăng nhập lại.", "SESSION_IDLE")
    # bug-030: phiên chờ TOTP quá 10 phút coi như hết hạn, tránh tồn đọng phiên dở
    if session.get("mfa_at") is None and now - session["created_at"] > timedelta(minutes=10):
        raise ConsoleAuthError("Phiên chờ nhập mã TOTP đã hết hạn, hãy đăng nhập lại.", "SESSION_EXPIRED")
    if require_mfa and session["mfa_at"] is None:
        raise ConsoleAuthError("Cần nhập mã TOTP.", "MFA_REQUIRED")


def step_up_fresh(step_up_at: datetime | None, now: datetime, window: timedelta) -> bool:
    return step_up_at is not None and now - step_up_at <= window
