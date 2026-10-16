"""Cấu hình AI Console nội bộ (ADR-0048)."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class ConsoleConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_CONSOLE_")

    # DB riêng `ai_console`, user riêng — KHÔNG trỏ vào AI_DATABASE_URL của
    # knowledge_*, để quyền console và tri thức Copilot không dùng chung tài khoản.
    database_url: str = ""

    # Chỉ dùng nội bộ (ADR-0048 §2): chạy native thì nghe loopback; trong Docker
    # process nghe 0.0.0.0 nhưng compose chỉ publish ra 127.0.0.1.
    bind_host: str = "127.0.0.1"
    port: int = 8090

    # OAuth client "Web application" tạo trên Google Cloud Console.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8090/console/api/auth/google/callback"

    # Khoá Fernet mã hoá secret TOTP trong DB; sinh bằng
    # `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    totp_encryption_key: str = ""
    totp_issuer: str = "IPLMS AI Console"

    session_ttl_hours: int = 8
    idle_timeout_minutes: int = 30
    step_up_minutes: int = 5
    # Localhost chạy http nên mặc định tắt; bật khi đặt sau TLS nội bộ.
    cookie_secure: bool = False

    # Ảnh cắt nhận qua A2 mà chưa ai gán nhãn ở console sẽ bị xoá sau N ngày (PII).
    vision_retention_days: int = 90
