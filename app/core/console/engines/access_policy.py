"""Danh mục vai trò/quyền của AI Console — MỘT nguồn (PROB-049 §3, ADR-0048).

Đăng nhập chỉ trả lời "người này là ai"; "được làm gì" quyết định ở đây, từ
vai trò lưu trong DB ``ai_console``. Admin/Moderator của platform không tự
động có vai trò nào trong này.
"""
from app.core.console.dtos import ConsoleActor
from app.core.exceptions import ConsoleAccessDenied

ANALYST = "ai_analyst"
ANNOTATOR = "ai_annotator"
REVIEWER = "ai_reviewer"
DATA_ENGINEER = "ai_data_engineer"
ML_ENGINEER = "ai_ml_engineer"
LEAD = "ai_lead"
CONSOLE_ADMIN = "ai_console_admin"

ROLES = (ANALYST, ANNOTATOR, REVIEWER, DATA_ENGINEER, ML_ENGINEER, LEAD, CONSOLE_ADMIN)

_PERMISSION_ROLES: dict[str, frozenset[str]] = {
    "ai:metrics:read": frozenset({ANALYST, REVIEWER, DATA_ENGINEER, ML_ENGINEER, LEAD}),
    "ai:task:label": frozenset({ANNOTATOR, REVIEWER}),
    "ai:label:approve": frozenset({REVIEWER, LEAD}),
    "ai:chatlog:read": frozenset({ANALYST, REVIEWER, ML_ENGINEER, LEAD}),
    "ai:pii:reveal": frozenset({DATA_ENGINEER, LEAD}),
    "ai:pipeline:manage": frozenset({DATA_ENGINEER, LEAD}),
    "ai:dataset:snapshot": frozenset({DATA_ENGINEER, ML_ENGINEER, LEAD}),
    "ai:golden:freeze": frozenset({LEAD}),
    "ai:model:evaluate": frozenset({ML_ENGINEER, LEAD}),
    "ai:model:propose": frozenset({ML_ENGINEER, LEAD}),
    "ai:model:promote": frozenset({LEAD}),
    "ai:prompt:edit": frozenset({ML_ENGINEER, LEAD}),
    "ai:policy:threshold": frozenset({LEAD}),
    "ai:member:manage": frozenset({CONSOLE_ADMIN}),
    "ai:audit:read": frozenset({LEAD, CONSOLE_ADMIN}),
}

PERMISSIONS = tuple(_PERMISSION_ROLES)

# Phải nhập lại TOTP gần đây + ghi lý do (ADR-0048 §4); phần kiểm thời gian ở P1b.
STEP_UP_PERMISSIONS = frozenset({
    "ai:pii:reveal", "ai:golden:freeze", "ai:model:promote", "ai:policy:threshold",
})


def validate_role(role: str) -> str:
    if role not in ROLES:
        raise ValueError("Vai trò console không hợp lệ.")
    return role


def can(actor: ConsoleActor, permission: str) -> bool:
    allowed = _PERMISSION_ROLES.get(permission)
    if allowed is None:
        # Gõ sai tên quyền phải lỗi ngay, không lặng lẽ trả False.
        raise ValueError(f"Quyền console không tồn tại: {permission}")
    return not actor.roles.isdisjoint(allowed)


def require(actor: ConsoleActor, permission: str) -> None:
    if not can(actor, permission):
        raise ConsoleAccessDenied("Bạn không có quyền thực hiện thao tác này.")


def require_second_person(actor: ConsoleActor, first_member_id: str) -> None:
    """Luật bốn mắt: người duyệt/cấp quyền phải khác người đề xuất/được cấp."""
    if actor.member_id == first_member_id:
        raise ConsoleAccessDenied("Thao tác này phải do một người khác thực hiện.")
