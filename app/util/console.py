"""Ép stdout/stderr sang UTF-8 trước khi in bất cứ thứ gì.

Console Windows có thể đang ở code page cp932/cp1252 (theo locale hệ thống).
Log tiếng Việt và emoji khi đó ném UnicodeEncodeError và **giết tiến trình ngay
lúc khởi động** — không phải lỗi hiển thị mà là lỗi chết người.
"""
import sys


def enable_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # stream đã bị thay bằng thứ không đổi được
            pass
