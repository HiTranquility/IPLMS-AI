"""Cấu hình logging dùng chung cho cả gRPC handler lẫn REST route."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class LoggingConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_LOG_")

    name: str = "IPLMS_AI"
    level: str = "INFO"
    format: str = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"
