"""Pydantic schemas cho AI Console Models & Connections REST routes."""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = [
    "Connection",
    "ConnectionCreate",
    "ConnectionDraft",
    "Reason",
    "TestResult",
]
