"""Cổng vào AI Console: cookie phiên, chống CSRF, kiểm quyền (ADR-0048 §4)."""
from fastapi import Request, Response

from app.config import get_config
from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.core.console import auth_service
from app.core.exceptions import ConsoleAccessDenied

SESSION_COOKIE = "ai_console_session"
FLOW_COOKIE = "ai_console_flow"
CSRF_HEADER = "x-console-request"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def session_token(request: Request) -> str:
    return request.cookies.get(SESSION_COOKIE, "")


def require_same_origin_write(request: Request) -> None:
    """Request ghi phải mang header tự đặt — form/ảnh từ site khác không gắn được header này."""
    if request.method in _SAFE_METHODS:
        return
    if request.headers.get(CSRF_HEADER) != "1":
        raise ConsoleAccessDenied("Thiếu header X-Console-Request.")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise ConsoleAccessDenied("Chỉ nhận request cùng nguồn.")


def require_permission(permission: str):
    console_auth_service.validate_permission(permission)

    async def dependency(request: Request) -> ConsoleActor:
        return await auth_service.authorize(session_token(request), permission)

    return dependency


def require_any_permission(*permissions: str):
    for permission in permissions:
        console_auth_service.validate_permission(permission)

    async def dependency(request: Request) -> ConsoleActor:
        return await auth_service.authorize_any(session_token(request), permissions)

    return dependency


def set_session_cookie(response: Response, raw: str) -> None:
    cfg = get_config().console
    response.set_cookie(
        SESSION_COOKIE, raw, max_age=cfg.session_ttl_hours * 3600, path="/",
        httponly=True, samesite="strict", secure=cfg.cookie_secure,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def set_flow_cookie(response: Response, browser: str) -> None:
    # Lax: phải đi kèm lần Google chuyển về callback (điều hướng cấp cao nhất, GET).
    response.set_cookie(
        FLOW_COOKIE, browser, max_age=600, path="/",
        httponly=True, samesite="lax", secure=get_config().console.cookie_secure,
    )


def clear_flow_cookie(response: Response) -> None:
    response.delete_cookie(FLOW_COOKIE, path="/")
