"""Cấu hình cache cục bộ cho model artifact đã lấy từ object storage."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class ModelRegistryConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_MODEL_REGISTRY_")

    # Tương đối so với thư mục ai/. Cache này là dữ liệu runtime, không commit.
    cache_dir: str = "var/model-cache"
