"""Cấu hình telemetry mỗi request AI (IPLMS ADR-0049, đề Final §4.2/§6.6)."""
from typing import Optional

from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class TelemetryConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_TELEMETRY_")

    enabled: bool = True
    # Khoá HMAC để lưu user id dạng băm: đếm/đối chiếu được mà không biết là ai.
    # Trống → không lưu user, và 👍/👎 không xác minh được chủ lượt nên bị từ chối.
    hmac_key: str = ""
    retention_days: int = 30

    # Giá USD trên 1 triệu token của model đang dùng. Không cấu hình → chi phí
    # để trống và dashboard hiện "—", không tự đặt giá tham chiếu.
    price_input_per_mtok: Optional[float] = None
    price_output_per_mtok: Optional[float] = None
