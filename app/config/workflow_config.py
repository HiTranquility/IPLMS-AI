"""Configuration for long-running Copilot workflows."""
from typing import Literal

from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class WorkflowConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_WORKFLOW_")

    enabled: bool = False
    checkpoint_backend: Literal["memory", "postgres"] = "memory"
    checkpoint_database_url: str = ""
    checkpoint_setup_schema: bool = False
    checkpoint_retention_days: int = 30
