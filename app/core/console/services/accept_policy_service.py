"""Ngưỡng tự nhận (accept_policy): đề xuất từ số đo thật, AI Lead duyệt bốn mắt (ISSUE-126 P5).

Console chỉ giữ phiên bản đã duyệt; backend kéo bản APPROVED gần nhất qua
`DatasetService.GetAcceptPolicy` mỗi chu kỳ worker A2 rồi áp vào `vision_data_policies`
(ADR-0051).
"""
from __future__ import annotations

import re

from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.core.console.engines.audit_accuracy import accuracy_report
from app.infra.database.console_vision_store import console_vision_store

DECISIONS = ("APPROVED", "REJECTED")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MODEL_NAME = "anpr"


def _reason(text: str) -> str:
    cleaned = (text or "").strip()
    if not 3 <= len(cleaned) <= 500:
        raise ValueError("Cần ghi lý do (3–500 ký tự).")
    return cleaned


class AcceptPolicyService:
    def __init__(self, store=None) -> None:
        self.store = store or console_vision_store

    async def accuracy(self, actor: ConsoleActor) -> dict:
        access_policy.require(actor, "ai:metrics:read")
        samples = await self.store.audit_samples()
        report = accuracy_report(samples)
        report["truth_sources"] = {
            "console": sum(1 for s in samples if s["truth_source"] == "console"),
            "moderator": sum(1 for s in samples if s["truth_source"] == "moderator"),
        }
        return report

    async def list_policies(self, actor: ConsoleActor) -> list[dict]:
        access_policy.require(actor, "ai:metrics:read")
        return await self.store.list_policies()

    async def propose(self, actor: ConsoleActor, threshold: float, audit_rate: float, reason: str) -> dict:
        access_policy.require(actor, "ai:model:propose")
        if not 0.5 <= threshold <= 0.99:
            raise ValueError("Ngưỡng tự nhận cần trong khoảng 0.50–0.99.")
        if not 0.01 <= audit_rate <= 0.5:
            raise ValueError("Tỉ lệ bốc kiểm cần trong khoảng 1%–50%.")
        report = accuracy_report(await self.store.audit_samples())
        # Lưu bằng chứng lúc đề xuất: người duyệt thấy đúng số người đề xuất đã thấy.
        at_threshold = next((c for c in report["curve"] if c["threshold"] == round(threshold, 2)), None)
        evidence = {
            "audit_total": report["total"], "audit_accuracy": report["accuracy"],
            "interval_95": report["interval_95"], "suggested_threshold": report["suggested_threshold"],
            "at_threshold": at_threshold,
        }
        return await self.store.propose_policy(
            MODEL_NAME, round(threshold, 2), round(audit_rate, 4), evidence, _reason(reason), actor.member_id
        )

    async def approved(self, model_name: str = MODEL_NAME) -> dict | None:
        """Cho RPC backend (không có actor console): chỉ đọc bản đã duyệt bốn mắt."""
        return await self.store.latest_approved_policy(model_name or MODEL_NAME)

    async def decide(self, actor: ConsoleActor, policy_id: str, decision: str, reason: str) -> None:
        # Step-up kiểm ở cổng REST (`ai:policy:threshold`); bốn mắt kiểm trong store.
        access_policy.require(actor, "ai:policy:threshold")
        if not _UUID.match(policy_id or ""):
            raise ValueError("policy_id không hợp lệ.")
        if decision not in DECISIONS:
            raise ValueError("Quyết định chỉ nhận APPROVED hoặc REJECTED.")
        await self.store.decide_policy(policy_id, actor.member_id, decision, _reason(reason))


accept_policy_service = AcceptPolicyService()
