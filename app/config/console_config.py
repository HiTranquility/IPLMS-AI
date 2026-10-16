"""Cấu hình AI Console nội bộ (ADR-0048)."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class ConsoleConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_CONSOLE_")

    # DB riêng `ai_console`, user riêng — KHÔNG trỏ vào AI_DATABASE_URL của
    # knowledge_*, để quyền console và tri thức Copilot không dùng chung tài khoản.
    database_url: str = ""
