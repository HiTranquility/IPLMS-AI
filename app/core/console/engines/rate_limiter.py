"""Giới hạn số lần gọi theo thành viên trong cửa sổ trượt (IPLMS ADR-0061 §7).

Bộ đếm nằm trong RAM của process console (Q-D đã chốt: console chạy một process).
Restart thì bộ đếm về 0; đây là chặn lạm dụng, không phải số liệu nghiệp vụ.
"""
from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Callable

from app.core.exceptions import ConsoleRateLimited


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0,
                 clock: Callable[[], float] = monotonic) -> None:
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str) -> None:
        """Ghi một lần gọi; vượt giới hạn thì ném `ConsoleRateLimited` và không tính lần đó."""
        now = self._clock()
        with self._lock:
            calls = self._calls[key]
            while calls and calls[0] <= now - self.window:
                calls.popleft()
            if len(calls) >= self.limit:
                raise ConsoleRateLimited(
                    f"Quá {self.limit} lần thử trong {int(self.window)} giây; thử lại sau."
                )
            calls.append(now)
