"""Copilot Lab của AI Console: số liệu, lượt chat đã che PII và chấm đúng/sai (ISSUE-126 P1c).

Lượt chat nằm ở `database-vector` (ADR-0049); kết quả chấm nằm ở DB `ai_console` kèm audit.
Tỉ lệ đúng chỉ tính trên các lượt đã được người chấm, không suy ra từ 👍/👎.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.core.copilot.services.usage_service import usage_service
from app.infra.database.ai_request_log_store import ai_request_log_store
from app.infra.database.console_store import console_store

VERDICTS = ("CORRECT", "INCORRECT", "UNSAFE")
STATUSES = ("SUCCESS", "REFUSED", "NO_CONTEXT", "ERROR")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _days(days: int) -> int:
    if not 1 <= days <= 90:
        raise ValueError("Cửa sổ thống kê cần trong khoảng 1–90 ngày.")
    return days


class ConsoleCopilotLabService:
    def __init__(self, usage=None, request_log=None, store=None) -> None:
        self.usage = usage or usage_service
        self.request_log = request_log or ai_request_log_store
        self.store = store or console_store

    async def usage_summary(self, actor: ConsoleActor, days: int):
        access_policy.require(actor, "ai:metrics:read")
        return await self.usage.summary(_days(days))

    async def review_stats(self, actor: ConsoleActor, days: int) -> dict:
        access_policy.require(actor, "ai:metrics:read")
        counts = await self.store.review_stats(_days(days))
        reviewed = sum(counts.get(v, 0) for v in VERDICTS)
        return {
            "window_days": days,
            "reviewed": reviewed,
            "correct": counts.get("CORRECT", 0),
            "incorrect": counts.get("INCORRECT", 0),
            "unsafe": counts.get("UNSAFE", 0),
            # None khi chưa chấm lượt nào: không có mẫu thì không có tỉ lệ.
            "accuracy": round(counts.get("CORRECT", 0) / reviewed, 4) if reviewed else None,
        }

    async def list_turns(
        self, actor: ConsoleActor, limit: int = 50, status: Optional[str] = None,
        feedback: Optional[int] = None, before: Optional[str] = None,
    ) -> list[dict]:
        access_policy.require(actor, "ai:chatlog:read")
        if not 1 <= limit <= 200:
            raise ValueError("Số lượt cần trong khoảng 1–200.")
        if status is not None and status not in STATUSES:
            raise ValueError("Trạng thái lượt không hợp lệ.")
        if feedback is not None and feedback not in (-1, 1):
            raise ValueError("feedback chỉ nhận 1 hoặc -1.")
        if before is not None:
            try:
                before = datetime.fromisoformat(before).isoformat()
            except ValueError:
                raise ValueError("Mốc `before` cần dạng ISO 8601.") from None
        turns = await self.request_log.list_recent(limit, status, feedback, before)
        reviews = await self.store.get_reviews([t["turn_id"] for t in turns])
        return [{**t, "review": reviews.get(t["turn_id"])} for t in turns]

    async def review_turn(
        self, actor: ConsoleActor, turn_id: str, verdict: str, note: str = ""
    ) -> None:
        access_policy.require(actor, "ai:label:approve")
        if not _UUID.match(turn_id or ""):
            raise ValueError("turn_id không hợp lệ.")
        if verdict not in VERDICTS:
            raise ValueError("Kết quả chấm chỉ nhận CORRECT, INCORRECT hoặc UNSAFE.")
        note = (note or "").strip()
        if len(note) > 500:
            raise ValueError("Ghi chú tối đa 500 ký tự.")
        if verdict != "CORRECT" and len(note) < 3:
            # Chấm sai/không an toàn mà không nói vì sao thì không dùng làm dữ liệu sửa được.
            raise ValueError("Chấm sai hoặc không an toàn cần ghi chú (≥ 3 ký tự).")
        turn_at = await self.request_log.turn_time(turn_id)
        if turn_at is None:
            raise ValueError("Không tìm thấy lượt này (có thể đã quá hạn lưu).")
        await self.store.review_turn(turn_id, turn_at, verdict, note, actor.member_id)


console_copilot_lab_service = ConsoleCopilotLabService()
