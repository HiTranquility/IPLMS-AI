"""Cấu hình AI Console nội bộ (ADR-0048)."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class ConsoleConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_CONSOLE_")

    # DB riêng `ai_console`, user riêng — KHÔNG trỏ vào AI_DATABASE_URL của
    # knowledge_*, để quyền console và tri thức Copilot không dùng chung tài khoản.
    database_url: str = ""

    # Database URL riêng cho process inference (ADR-0051): gRPC server dùng URL này
    # với user bị siết quyền ai_inference (chỉ bảng A2 và đọc accept_policy).
    # Nếu để trống, fallback về database_url.
    inference_database_url: str = ""

    # Chỉ dùng nội bộ (ADR-0048 §2): chạy native thì nghe loopback; trong Docker
    # process nghe 0.0.0.0 nhưng compose chỉ publish ra 127.0.0.1.
    bind_host: str = "127.0.0.1"
    port: int = 8090
    # Reloader theo dõi file chỉ cho máy dev, bật rõ bằng AI_CONSOLE_RELOAD=true.
    reload: bool = False

    # OAuth client "Web application" tạo trên Google Cloud Console.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8090/api/auth/google/callback"

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

    # Nút "nạp mẫu thực hành" ở Vision Lab ghi mẫu `purpose='train'` vào DB;
    # chỉ bật ở dev/sandbox (compose develop), production để mặc định tắt.
    demo_seed_enabled: bool = False

    # Models & Connections (IPLMS ADR-0061 §7): host được phép làm endpoint connection,
    # phân cách bằng dấu phẩy, khớp đúng tên (vd `host.docker.internal,api.openai.com`).
    # Rỗng = không host nào (đóng mặc định). Link-local/metadata luôn bị chặn.
    model_connection_hosts: str = ""
    # Tên biến env chứa key ngoài tiền tố AI_LLM_KEY_ (vd `AI_LLM_API_KEY`), phân cách dấu phẩy.
    model_secret_names: str = ""
    model_test_timeout_seconds: float = 10.0
    model_tests_per_minute: int = 10
