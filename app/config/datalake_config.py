"""Cấu hình Domain Forecast: kho Parquet log phiên đỗ dùng để huấn luyện/dự báo."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class DatalakeConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_DATALAKE_")

    # Operational PostgreSQL is a separate trust/data boundary from the
    # pgvector knowledge database used by Copilot. Keep its URL explicit so a
    # training export can never silently read AI_DATABASE_URL.
    source_database_url: str = ""
    s3_bucket: str = "iplms-datalake"
    local_path: str = "data/datalake"
    export_batch_size: int = 1000
    occupancy_slot_minutes: int = 30
