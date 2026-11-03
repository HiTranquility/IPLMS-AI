"""Pydantic schemas cho AI Console Member & Audit REST routes."""
from typing import List

from pydantic import BaseModel, Field


class Invite(BaseModel):
    email: str = Field(max_length=254)
    display_name: str = Field(max_length=120)
    reason: str = Field(max_length=500)


class RoleChange(BaseModel):
    reason: str = Field(max_length=500)


class Member(BaseModel):
    id: str
    email: str
    display_name: str
    status: str
    created_at: str
    roles: List[str]


class Changed(BaseModel):
    changed: bool


class AuditEntry(BaseModel):
    id: str
    actor_id: str
    action: str
    target_type: str
    target_id: str
    reason: str
    at: str


__all__ = [
    "AuditEntry",
    "Changed",
    "Invite",
    "Member",
    "RoleChange",
]
