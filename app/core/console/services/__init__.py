"""Services của AI Console nội bộ (ADR-0048)."""
from app.core.console.services.accept_policy_service import console_accept_policy_service
from app.core.console.services.auth_service import console_auth_service
from app.core.console.services.copilot_lab_service import console_copilot_lab_service
from app.core.console.services.member_service import console_member_service
from app.core.console.services.model_connection_service import console_model_connection_service
from app.core.console.services.model_lab_service import console_model_lab_service
from app.core.console.services.tools_service import console_tools_service
from app.core.console.services.vision_import_service import console_vision_import_service
from app.core.console.services.vision_lab_service import console_vision_lab_service

__all__ = [
    "console_accept_policy_service",
    "console_auth_service",
    "console_copilot_lab_service",
    "console_member_service",
    "console_model_connection_service",
    "console_model_lab_service",
    "console_tools_service",
    "console_vision_import_service",
    "console_vision_lab_service",
]
