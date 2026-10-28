"""Models & Connections trong AI Console (ISSUE-022 chặng 2, IPLMS REQ-020 F2–F3, ADR-0061)."""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.rest.console_access import require_permission
from app.api.rest.schemas.base_response import BaseResponse
from app.core.console import ConsoleActor, console_model_connection_service

router = APIRouter(prefix="/models", tags=["AI Console models"])


class ConnectionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="Thử nhanh", max_length=80)
    provider: str = Field(max_length=16)
    base_url: str = Field(max_length=500)
    # Tên biến env chứa key trên AI host — KHÔNG phải giá trị key (ADR-0061 §6).
    secret_env_name: str = Field(default="", max_length=64)


class ConnectionCreate(ConnectionDraft):
    name: str = Field(max_length=80)
    reason: str = Field(max_length=300)
    replaces_id: str = Field(default="", max_length=36)


class Reason(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(max_length=300)


class Connection(BaseModel):
    id: str
    name: str
    provider: str
    base_url: str
    secret_env_name: str
    status: str
    replaces_id: str
    created_by: str
    created_at: str
    disabled_by: str
    disabled_at: str
    last_tested_at: str
    last_test_ok: Optional[bool]
    last_test_error: str
    last_test_latency_ms: Optional[int]
    last_test_models: List[str]


class TestResult(BaseModel):
    ok: bool
    error: str
    latency_ms: Optional[int]
    models: List[str]
    detail: str


@router.get("/connections", response_model=BaseResponse[Connection])
async def list_connections(
    actor: ConsoleActor = Depends(require_permission("ai:metrics:read")),
) -> BaseResponse[Connection]:
    rows = await console_model_connection_service.list_connections(actor)
    return BaseResponse.ok([Connection(**r) for r in rows], "OK")


@router.post("/connections", response_model=BaseResponse[Connection])
async def create_connection(
    payload: ConnectionCreate, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
) -> BaseResponse[Connection]:
    data = payload.model_dump(exclude={"reason", "replaces_id"})
    row = await console_model_connection_service.create_connection(
        actor, data, payload.reason, payload.replaces_id,
    )
    return BaseResponse.ok([Connection(**row)], "Đã lưu connection.")


@router.post("/connections/test", response_model=BaseResponse[TestResult])
async def test_draft(
    payload: ConnectionDraft, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
) -> BaseResponse[TestResult]:
    result = await console_model_connection_service.test_draft(actor, payload.model_dump())
    return BaseResponse.ok([TestResult(**result)], "OK" if result["ok"] else "Thử kết nối không đạt.")


@router.post("/connections/{connection_id}/test", response_model=BaseResponse[TestResult])
async def test_connection(
    connection_id: str, actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
) -> BaseResponse[TestResult]:
    result = await console_model_connection_service.test_connection(actor, connection_id)
    return BaseResponse.ok([TestResult(**result)], "OK" if result["ok"] else "Thử kết nối không đạt.")


@router.post("/connections/{connection_id}/disable", response_model=BaseResponse[Connection])
async def disable_connection(
    connection_id: str, payload: Reason,
    actor: ConsoleActor = Depends(require_permission("ai:model:propose")),
) -> BaseResponse[Connection]:
    row = await console_model_connection_service.disable_connection(actor, connection_id, payload.reason)
    return BaseResponse.ok([Connection(**row)], "Đã tắt connection.")
