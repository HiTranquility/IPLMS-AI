"""Đăng nhập AI Console: Google → TOTP, mật khẩu khẩn cấp, step-up, đăng xuất, /me."""
from typing import List, Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.api.rest.console_access import (
    FLOW_COOKIE, clear_flow_cookie, clear_session_cookie, session_token,
    set_flow_cookie, set_session_cookie,
)
from app.api.rest.schemas.base_response import BaseResponse
from app.core.console.engines import access_policy
from app.core.console.services import console_auth_service
from app.core.exceptions import ConsoleAuthError

router = APIRouter(tags=["AI Console auth"])

_UI_HOME = "/console/"


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


@router.get("/auth/google/start")
async def google_start() -> RedirectResponse:
    url, browser = await console_auth_service.start_google()
    response = RedirectResponse(url, status_code=302)
    set_flow_cookie(response, browser)
    return response


@router.get("/auth/google/callback")
async def google_callback(
    request: Request, code: Optional[str] = None, state: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    # Lỗi chỉ trả mã ngắn trên URL — không đưa thông điệp/token vào query.
    if error:
        response = RedirectResponse(f"{_UI_HOME}?login_error=GOOGLE_DENIED", status_code=302)
    else:
        try:
            raw = await console_auth_service.finish_google(
                code or "", state or "", request.cookies.get(FLOW_COOKIE, "")
            )
        except ConsoleAuthError as exc:
            response = RedirectResponse(f"{_UI_HOME}?login_error={exc.code}", status_code=302)
        else:
            response = RedirectResponse(_UI_HOME, status_code=302)
            set_session_cookie(response, raw)
    clear_flow_cookie(response)
    return response


@router.post("/auth/password", response_model=BaseResponse[LoginState])
async def password_login(payload: PasswordLogin, response: Response) -> BaseResponse[LoginState]:
    raw = await console_auth_service.password_login(payload.email, payload.password)
    set_session_cookie(response, raw)
    return BaseResponse.ok([LoginState(mfa_required=True)], "Nhập mã TOTP để hoàn tất đăng nhập.")


@router.post("/auth/totp/enroll", response_model=BaseResponse[Enrollment])
async def totp_enroll(request: Request) -> BaseResponse[Enrollment]:
    uri = await console_auth_service.totp_enrollment_uri(session_token(request))
    return BaseResponse.ok([Enrollment(otpauth_uri=uri)], "Quét mã bằng ứng dụng xác thực.")


@router.post("/auth/totp", response_model=BaseResponse[LoginState])
async def totp_verify(request: Request, payload: TotpCode) -> BaseResponse[LoginState]:
    await console_auth_service.verify_totp(session_token(request), payload.code)
    return BaseResponse.ok([LoginState(mfa_required=False)], "Đã đăng nhập console.")


@router.post("/auth/step-up", response_model=BaseResponse[LoginState])
async def step_up(request: Request, payload: StepUp) -> BaseResponse[LoginState]:
    await console_auth_service.step_up(session_token(request), payload.code, payload.reason)
    return BaseResponse.ok([LoginState(mfa_required=False)], "Đã xác thực lại.")


@router.post("/auth/logout", response_model=BaseResponse[LoginState])
async def logout(request: Request, response: Response) -> BaseResponse[LoginState]:
    await console_auth_service.logout(session_token(request))
    clear_session_cookie(response)
    return BaseResponse.ok([], "Đã đăng xuất.")


@router.get("/me", response_model=BaseResponse[Me])
async def me(request: Request) -> BaseResponse[Me]:
    session = await console_auth_service.resolve(session_token(request), require_mfa=False)
    permissions = (
        [p for p in access_policy.PERMISSIONS if access_policy.can(session.actor, p)]
        if session.mfa_done else []
    )
    return BaseResponse.ok([Me(
        member_id=session.actor.member_id, email=session.email,
        display_name=session.display_name, roles=sorted(session.actor.roles),
        permissions=permissions, mfa_done=session.mfa_done, totp_enabled=session.totp_enabled,
        totp_pending=session.totp_secret_set and not session.totp_enabled,
    )], "OK")
