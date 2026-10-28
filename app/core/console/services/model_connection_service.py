"""Connection tới provider LLM trong Models & Connections (ISSUE-022 chặng 2, IPLMS ADR-0061).

Dữ liệu ở `ai-db` (`ai_model_connections`, qua `ModelPolicyStore`); audit ở DB
`ai_console` như mọi thao tác console khác. Connection chỉ lưu TÊN biến secret;
giá trị key chỉ được đọc trên AI host lúc thử và không bao giờ ra response/log/audit.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Callable, Optional

from app.config import get_config
from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.core.console.engines.rate_limiter import SlidingWindowLimiter
from app.core.console.guardrails import model_endpoint
from app.infra.database.console_store import console_store
from app.infra.database.model_policy_store import model_policy_store
from app.infra.llm import connection_probe

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _reason(text: str) -> str:
    cleaned = (text or "").strip()
    if not 3 <= len(cleaned) <= 300:
        raise ValueError("Cần ghi lý do (3–300 ký tự).")
    return cleaned


def _uuid(value: str) -> str:
    if not _UUID.match(value or ""):
        raise ValueError("connection_id không hợp lệ.")
    return value


def _summary(values: dict[str, Any]) -> str:
    # Chỉ tên biến secret, không bao giờ là giá trị (ADR-0061 §6).
    return (
        f"name={values['name']}, provider={values['provider']}, base_url={values['base_url']}, "
        f"secret_env_name={values['secret_env_name'] or '-'}"
    )


class ConsoleModelConnectionService:
    def __init__(
        self, store=None, audit_store=None,
        probe: Optional[Callable[..., dict[str, Any]]] = None,
        limiter: Optional[SlidingWindowLimiter] = None,
    ) -> None:
        self.store = store or model_policy_store
        self.audit = audit_store or console_store
        self._probe = probe or connection_probe.probe
        self._limiter = limiter

    @staticmethod
    def _cfg():
        return get_config().console

    def _limit(self, actor: ConsoleActor) -> None:
        if self._limiter is None:
            self._limiter = SlidingWindowLimiter(self._cfg().model_tests_per_minute)
        self._limiter.hit(actor.member_id)

    def _clean(self, data: dict[str, Any]) -> dict[str, Any]:
        cfg = self._cfg()
        return model_endpoint.clean_connection(
            data, model_endpoint.allowed_hosts(cfg.model_connection_hosts), cfg.model_secret_names,
        )

    async def list_connections(self, actor: ConsoleActor) -> list[dict[str, Any]]:
        access_policy.require(actor, "ai:metrics:read")
        return await self.store.list_connections()

    async def create_connection(
        self, actor: ConsoleActor, data: dict[str, Any], reason: str,
        replaces_id: str = "",
    ) -> dict[str, Any]:
        access_policy.require(actor, "ai:model:propose")
        why = _reason(reason)
        values = self._clean(data)
        replaces = _uuid(replaces_id) if replaces_id else None
        row = await self.store.create_connection(values, actor.member_id, replaces)
        before = f" | thay {replaces}" if replaces else ""
        await self.audit.add_audit(
            actor.member_id, "model.connection_create", "model_connection", row["id"],
            f"{why} | {_summary(values)}{before}",
        )
        return row

    async def disable_connection(self, actor: ConsoleActor, connection_id: str, reason: str) -> dict[str, Any]:
        access_policy.require(actor, "ai:model:propose")
        why = _reason(reason)
        row = await self.store.disable_connection(_uuid(connection_id), actor.member_id)
        await self.audit.add_audit(
            actor.member_id, "model.connection_disable", "model_connection", row["id"], why,
        )
        return row

    async def _run_probe(self, values: dict[str, Any]) -> dict[str, Any]:
        timeout = self._cfg().model_test_timeout_seconds
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._probe, values["provider"], values["base_url"], values["secret_env_name"],
                    model_endpoint.check_resolved_addresses, timeout,
                ),
                timeout + 1,
            )
        except asyncio.TimeoutError:
            return {"ok": False, "error": "timeout", "latency_ms": int(timeout * 1000),
                    "models": [], "detail": ""}

    async def test_connection(self, actor: ConsoleActor, connection_id: str) -> dict[str, Any]:
        access_policy.require(actor, "ai:model:propose")
        connection = await self.store.get_connection(_uuid(connection_id))
        if connection is None:
            raise ValueError("Không tìm thấy connection.")
        self._limit(actor)
        values = {k: connection[k] for k in ("name", "provider", "base_url", "secret_env_name")}
        try:
            # Allowlist có thể đã đổi sau khi tạo: kiểm lại trước mỗi lần thử.
            self._clean(values)
        except model_endpoint.BlockedEndpoint as exc:
            result = {"ok": False, "error": "blocked_host", "latency_ms": None, "models": [],
                      "detail": str(exc)}
        else:
            result = await self._run_probe(values)
        await self.store.record_connection_test(connection["id"], result)
        await self.audit.add_audit(
            actor.member_id, "model.connection_test", "model_connection", connection["id"],
            f"ok={result['ok']} error={result['error'] or '-'} models={len(result['models'])}",
        )
        return result

    async def test_draft(self, actor: ConsoleActor, data: dict[str, Any]) -> dict[str, Any]:
        """Thử connection chưa lưu: không ghi bảng nào ở `ai-db`, chỉ audit (Q-F)."""
        access_policy.require(actor, "ai:model:propose")
        self._limit(actor)
        # Bản nháp chưa cần tên; tên chỉ bắt buộc khi lưu.
        data = {**data, "name": (data.get("name") or "").strip() or "Thử nhanh"}
        try:
            values = self._clean(data)
        except model_endpoint.BlockedEndpoint as exc:
            result = {"ok": False, "error": "blocked_host", "latency_ms": None, "models": [],
                      "detail": str(exc)}
            values = None
        else:
            result = await self._run_probe(values)
        await self.audit.add_audit(
            actor.member_id, "model.connection_test", "model_connection", "draft",
            f"ok={result['ok']} error={result['error'] or '-'} "
            f"{_summary(values) if values else 'endpoint bị chặn'}",
        )
        return result


console_model_connection_service = ConsoleModelConnectionService()
