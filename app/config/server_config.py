"""Cấu hình 2 transport: gRPC server (backend NestJS gọi vào) và FastAPI REST."""
from typing import List

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig

_10_MB = 10 * 1024 * 1024


class ServerConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_")

    grpc_bind_host: str = "[::]"
    grpc_port: int = 50051
    grpc_max_workers: int = 10
    # Trần RPC đồng thời (bug-046), tính cả stream Copilot đang mở và health check.
    # Rộng hơn grpc_max_workers vì stream chủ yếu chờ LLM, không giữ luồng CPU.
    grpc_maximum_concurrent_rpcs: int = Field(50, ge=1)
    # Ảnh cổng đi thẳng trong message → phải khớp AI_GRPC_MAX_MESSAGE_MB bên NestJS.
    grpc_max_message_length: int = _10_MB
    fastapi_port: int = 8000
    # Origin trình duyệt được gọi REST inference, phân tách bằng dấu phẩy (bug-045).
    # Mặc định rỗng: backend gọi server-to-server, không trình duyệt nào gọi thẳng :8000.
    # [NEVER] đặt "*": AI không có xác thực nên mọi trang web sẽ đọc được phản hồi.
    cors_allow_origins: str = ""

    @property
    def cors_allow_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    # Bật route chẩn đoán Vision local (`/api/vision/*`, chỉ loopback). Tên giữ nguyên để
    # không đổi biến môi trường; trang `/dashboard` cũ đã dời vào AI Console (IPLMS ADR-0050).
    # [NEVER] bật trên service dùng chung/production.
    developer_dashboard_enabled: bool = False
    # Token xác thực nội bộ service-to-server (`x-internal-token` trong gRPC metadata).
    # Khi để rỗng (dev mặc định) thì không bắt buộc; khi đặt giá trị thì mọi RPC trừ
    # `/grpc.health.v1.Health/Check` phải kèm header khớp hằng thời gian (REQ-038).
    internal_api_token: str = ""
