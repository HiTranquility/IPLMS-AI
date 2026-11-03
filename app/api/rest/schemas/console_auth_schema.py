"""Pydantic schemas cho AI Console Auth REST routes."""
from typing import List

from pydantic import BaseModel, Field


class PasswordLogin(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class TotpCode(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class StepUp(TotpCode):
    reason: str = Field(max_length=500)


class LoginState(BaseModel):
    mfa_required: bool


class Enrollment(BaseModel):
    otpauth_uri: str


class Me(BaseModel):
    member_id: str
    email: str
    display_name: str
    roles: List[str]
    permissions: List[str]
    mfa_done: bool
    totp_enabled: bool
    # Đã có khoá (từ CLI) nhưng chưa xác nhận: nhập mã luôn, không tạo khoá mới.
    totp_pending: bool


__all__ = [
    "Enrollment",
    "LoginState",
    "Me",
    "PasswordLogin",
    "StepUp",
    "TotpCode",
]
