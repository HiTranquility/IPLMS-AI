"""Models & Connections trong AI Console (ISSUE-022 chặng 2, IPLMS REQ-020 F2–F3, ADR-0061)."""
from fastapi import APIRouter, Depends

from app.api.rest.console_access import require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.api.rest.schemas.console_model_schema import (
    Connection,
    ConnectionCreate,
    ConnectionDraft,
    Reason,
    TestResult,
)
from app.core.console import ConsoleActor, model_connection_service

router = APIRouter(prefix="/models", tags=["AI Console models"])


@router.get("/connections", response_model=BaseResponse[Connection])
async def list_connections(
    actor: ConsoleActor = Depends(require_permission("ai:metrics:read")),
) -> BaseResponse[Connection]:
    rows = await model_connection_service.list_connections(actor)
    return BaseResponse.ok([Connection(**r) for r in rows], "OK")


@router.post("/connections", response_model=BaseResponse[Connection])
async def create_connection(
    payload: ConnectionCreate, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
) -> BaseResponse[Connection]:
    data = payload.model_dump(exclude={"reason", "replaces_id"})
    row = await model_connection_service.create_connection(
        actor, data, payload.reason, payload.replaces_id,
    )
    return BaseResponse.ok([Connection(**row)], "Đã lưu connection.")


@router.post("/connections/test", response_model=BaseResponse[TestResult])
async def test_draft(
    payload: ConnectionDraft, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
) -> BaseResponse[TestResult]:
    result = await model_connection_service.test_draft(actor, payload.model_dump())
    return BaseResponse.ok([TestResult(**result)], "OK" if result["ok"] else "Thử kết nối không đạt.")


@router.post("/connections/{connection_id}/test", response_model=BaseResponse[TestResult])
async def test_connection(
    connection_id: str, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
) -> BaseResponse[TestResult]:
    result = await model_connection_service.test_connection(actor, connection_id)
    return BaseResponse.ok([TestResult(**result)], "OK" if result["ok"] else "Thử kết nối không đạt.")


@router.post("/connections/{connection_id}/disable", response_model=BaseResponse[Connection])
async def disable_connection(
    connection_id: str, payload: Reason,
    actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
) -> BaseResponse[Connection]:
    row = await model_connection_service.disable_connection(actor, connection_id, payload.reason)
    return BaseResponse.ok([Connection(**row)], "Đã tắt connection.")
