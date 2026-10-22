"""Telemetry mỗi lượt hỏi Copilot + 👍/👎 + tóm tắt cho dashboard (IPLMS ADR-0049).

Ghi telemetry chạy nền: DB chậm hay lỗi không được làm chậm hoặc hỏng câu trả
lời của người dùng — mất một dòng log còn hơn mất một câu trả lời.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
import time
from typing import Any, Optional

from app.config import get_config
from app.core.copilot.dtos.copilot_dto import AskQuestionRequest, UsageDay, UsageSummary
from app.core.copilot.engines.pii_redactor import redact
from app.core.copilot.engines.rag_pipeline import PROMPT_VERSION, TOOLS
from app.infra.database.ai_request_log_store import ai_request_log_store
from app.util.logger import logger

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_MAX_TEXT = 4000


class CopilotUsageService:
    def __init__(self, store=None, config=None) -> None:
        self.store = store or ai_request_log_store
        self._config = config or get_config().telemetry
        self._pending: set[asyncio.Task] = set()

    def user_hash(self, user_id: str) -> Optional[str]:
        if not self._config.hmac_key or not user_id:
            return None
        return hmac.new(self._config.hmac_key.encode("utf-8"), user_id.encode("utf-8"),
                        hashlib.sha256).hexdigest()

    def cost(self, input_tokens: Optional[int], output_tokens: Optional[int]) -> Optional[float]:
        price_in, price_out = self._config.price_input_per_mtok, self._config.price_output_per_mtok
        if price_in is None or price_out is None or input_tokens is None or output_tokens is None:
            return None
        return round(input_tokens / 1_000_000 * price_in + output_tokens / 1_000_000 * price_out, 6)

    def build_entry(
        self, *, turn_id: str, task: str, status: str, started: float,
        request: AskQuestionRequest, result: dict[str, Any] | None = None,
        answer: str = "", error_code: str | None = None,
    ) -> dict[str, Any]:
        result = result or {}
        usage = result.get("usage") or {}
        tokens_in = result.get("input_tokens") or usage.get("input_tokens")
        tokens_out = result.get("output_tokens") or usage.get("output_tokens")
        return {
            "turn_id": turn_id,
            "task": task,
            "status": status,
            "model": result.get("model", ""),
            "model_revision": result.get("model_revision", ""),
            "prompt_version": PROMPT_VERSION,
            "tools": TOOLS if status in ("SUCCESS", "REFUSED", "NO_CONTEXT") else [],
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "cost_usd": self.cost(tokens_in, tokens_out),
            "user_hash": self.user_hash(request.user_id),
            "user_role": (request.user_role or "")[:16],
            "parking_lot_id": request.parking_lot_id,
            "query_redacted": redact(request.query)[:_MAX_TEXT],
            "answer_redacted": redact(answer)[:_MAX_TEXT] if answer else None,
            "error_code": error_code,
        }

    async def _record(self, entry: dict[str, Any]) -> None:
        try:
            await self.store.record(entry)
        except Exception as exc:  # telemetry không được làm hỏng lượt hỏi
            logger.warning("Không ghi được telemetry AI: %s", type(exc).__name__)

    def record_soon(self, entry: dict[str, Any]) -> None:
        if not self._config.enabled:
            return
        task = asyncio.get_running_loop().create_task(self._record(entry))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def drain(self) -> None:
        """Chờ các lượt ghi đang chạy (dùng khi tắt service và trong test)."""
        if self._pending:
            await asyncio.gather(*list(self._pending), return_exceptions=True)

    async def feedback(self, turn_id: str, user_id: str, rating: int) -> bool:
        if rating not in (-1, 1):
            raise ValueError("rating chỉ nhận 1 (👍) hoặc -1 (👎).")
        if not _UUID.match(turn_id or ""):
            raise ValueError("turn_id không hợp lệ.")
        user_hash = self.user_hash(user_id)
        if user_hash is None:
            return False
        return await self.store.set_feedback(turn_id, user_hash, rating)

    async def summary(self, days: int) -> UsageSummary:
        if not 1 <= days <= 90:
            raise ValueError("Cửa sổ thống kê cần trong khoảng 1–90 ngày.")
        data = await self.store.summary(days)
        return UsageSummary(**{**data, "days": [UsageDay(**d) for d in data["days"]]})


usage_service = CopilotUsageService()
