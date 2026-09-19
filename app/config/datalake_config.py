"""Cấu hình Domain Forecast: kho Parquet log phiên đỗ dùng để huấn luyện/dự báo."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class DatalakeConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_DATALAKE_")

    s3_bucket: str = "iplms-datalake"
    local_path: str = "data/datalake"
