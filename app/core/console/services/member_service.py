"""Mời thành viên, cấp/thu hồi vai trò và đọc nhật ký của AI Console."""
from __future__ import annotations

import re

from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.infra.database.console_store import console_store

_EMAIL = re.compile(r"[^@\s]{1,64}@[^@\s]{1,189}\.[^@\s]{2,}")


def _reason(reason: str) -> str:
    cleaned = (reason or "").strip()
    if not 3 <= len(cleaned) <= 500:
        raise ValueError("Cần ghi lý do (3–500 ký tự) cho thao tác này.")
    return cleaned


class MemberService:
    def __init__(self, store=None) -> None:
        self.store = store or console_store

    async def invite(
        self, actor: ConsoleActor, email: str, display_name: str, reason: str
    ) -> dict:
        access_policy.require(actor, "ai:member:manage")
        email = (email or "").strip()
        display_name = (display_name or "").strip()
        if not _EMAIL.fullmatch(email):
            raise ValueError("Email không hợp lệ.")
        if not 1 <= len(display_name) <= 120:
            raise ValueError("Tên hiển thị cần 1–120 ký tự.")
        return await self.store.invite_member(email, display_name, actor.member_id, _reason(reason))

    async def grant_role(
        self, actor: ConsoleActor, member_id: str, role: str, reason: str
    ) -> bool:
        access_policy.require(actor, "ai:member:manage")
        # Admin quản người, không tự cấp quyền cho chính mình (ADR-0048).
        access_policy.require_second_person(actor, member_id)
        return await self.store.grant_role(
            member_id, access_policy.validate_role(role), actor.member_id, _reason(reason)
        )

    async def revoke_role(
        self, actor: ConsoleActor, member_id: str, role: str, reason: str
    ) -> bool:
        access_policy.require(actor, "ai:member:manage")
        return await self.store.revoke_role(
            member_id, access_policy.validate_role(role), actor.member_id, _reason(reason)
        )

    async def list_members(self, actor: ConsoleActor) -> list[dict]:
        access_policy.require(actor, "ai:member:manage")
        return await self.store.list_members()

    async def list_audit(self, actor: ConsoleActor, limit: int = 100) -> list[dict]:
        access_policy.require(actor, "ai:audit:read")
        if not 1 <= limit <= 500:
            raise ValueError("Số dòng nhật ký cần trong khoảng 1–500.")
        return await self.store.list_audit(limit)


member_service = MemberService()
