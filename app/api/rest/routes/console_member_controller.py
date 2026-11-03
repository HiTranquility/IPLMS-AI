"""Quản lý thành viên/vai trò và đọc nhật ký AI Console (P1a qua REST)."""
from fastapi import APIRouter, Depends, Query

from app.api.rest.console_access import require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.api.rest.schemas.console_member_schema import (
    AuditEntry,
    Changed,
    Invite,
    Member,
    RoleChange,
)
from app.core.console.dtos import ConsoleActor
from app.core.console import member_service

router = APIRouter(tags=["AI Console members"])


@router.get("/members", response_model=BaseResponse[Member])
async def list_members(
    actor: ConsoleActor = Depends(require_permission("ai:member:manage")),
) -> BaseResponse[Member]:
    members = await member_service.list_members(actor)
    return BaseResponse.ok([Member(**m) for m in members], "OK")


@router.post("/members", response_model=BaseResponse[Member])
async def invite(
    payload: Invite, actor: ConsoleActor = Depends(require_permission("ai:member:manage"))
) -> BaseResponse[Member]:
    member = await member_service.invite(
        actor, payload.email, payload.display_name, payload.reason
    )
    return BaseResponse.ok([Member(**member)], "Đã mời thành viên.")


@router.post("/members/{member_id}/roles/{role}", response_model=BaseResponse[Changed])
async def grant_role(
    member_id: str, role: str, payload: RoleChange,
    actor: ConsoleActor = Depends(require_permission("ai:member:manage")),
) -> BaseResponse[Changed]:
    changed = await member_service.grant_role(actor, member_id, role, payload.reason)
    return BaseResponse.ok([Changed(changed=changed)], "Đã cấp vai trò." if changed else "Đã có vai trò này.")


@router.post("/members/{member_id}/roles/{role}/revoke", response_model=BaseResponse[Changed])
async def revoke_role(
    member_id: str, role: str, payload: RoleChange,
    actor: ConsoleActor = Depends(require_permission("ai:member:manage")),
) -> BaseResponse[Changed]:
    changed = await member_service.revoke_role(actor, member_id, role, payload.reason)
    return BaseResponse.ok([Changed(changed=changed)], "Đã thu hồi vai trò." if changed else "Không có vai trò này.")


@router.get("/audit", response_model=BaseResponse[AuditEntry])
async def audit(
    limit: int = Query(100, ge=1, le=500),
    actor: ConsoleActor = Depends(require_permission("ai:audit:read")),
) -> BaseResponse[AuditEntry]:
    entries = await member_service.list_audit(actor, limit)
    return BaseResponse.ok([AuditEntry(**e) for e in entries], "OK")
