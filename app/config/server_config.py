"""Cấu hình 2 transport: gRPC server (backend NestJS gọi vào) và FastAPI REST."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig

_10_MB = 10 * 1024 * 1024


class ServerConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_")

    grpc_bind_host: str = "[::]"
    grpc_port: int = 50051
    grpc_max_workers: int = 10
    # Ảnh cổng đi thẳng trong message → phải khớp AI_GRPC_MAX_MESSAGE_MB bên NestJS.
    grpc_max_message_length: int = _10_MB
    fastapi_port: int = 8000

    # Bật route chẩn đoán Vision local (`/api/vision/*`, chỉ loopback). Tên giữ nguyên để
    # không đổi biến môi trường; trang `/dashboard` cũ đã dời vào AI Console (IPLMS ADR-0050).
    # [NEVER] bật trên service dùng chung/production.
    developer_dashboard_enabled: bool = False
