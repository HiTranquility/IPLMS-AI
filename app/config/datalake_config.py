"""Cấu hình Domain Forecast: kho Parquet log phiên đỗ dùng để huấn luyện/dự báo."""
from pydantic import AliasChoices, Field
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
    # Biến môi trường di sản cho đường dẫn Gold Data Lake (ưu tiên trước analytic/var/datalake).
    legacy_lake_dir: str = Field(
        default="",
        validation_alias=AliasChoices("DATALAKE_DIR", "AI_DATALAKE_PATH", "LAKE_LOCAL_FALLBACK_DIR"),
    )
    export_batch_size: int = 1000
    occupancy_slot_minutes: int = 30
