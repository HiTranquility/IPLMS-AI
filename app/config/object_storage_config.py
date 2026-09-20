"""Cấu hình tải artifact qua signed URL của S3/MinIO/R2."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class ObjectStorageConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_OBJECT_STORAGE_")

    download_timeout_seconds: int = 120
    max_artifact_mb: int = 2048
    allow_insecure_http: bool = False

    @property
    def max_artifact_bytes(self) -> int:
        return self.max_artifact_mb * 1024 * 1024
