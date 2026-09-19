"""Cấu hình sinh embedding cho RAG: model, số chiều, kích thước lô.

[GOTCHA] `dimensions` KHÔNG phải một con số tuỳ chỉnh được sau khi đã nạp liệu.
Cột `knowledge_chunks.embedding` khai `vector(1536)`, nên đổi model sang loại
có số chiều khác đồng nghĩa phải **embed lại toàn bộ** tài liệu đã nạp. Xem
ngã rẽ A của docs/suggestions/09-2026/SUGGESTION-008-knowledge-ingestion-pipeline.md.

API key KHÔNG nằm ở đây mà dùng chung `LlmConfig.llm_api_key`: cùng một tài
khoản OpenAI phục vụ cả embedding lẫn sinh câu trả lời, tách làm hai biến chỉ
tạo cơ hội cho chúng lệch nhau.
"""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class EmbeddingConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_EMBEDDING_")

    model: str = "text-embedding-3-small"

    # Phải khớp `vector(N)` của cột embedding trong DB. Đổi số này mà không
    # migration + embed lại thì mọi lượt ghi sẽ hỏng ở tầng DB.
    dimensions: int = 1536

    # Số đoạn gửi trong một lần gọi API. OpenAI nhận nhiều đoạn/request, gửi
    # từng đoạn một sẽ biến tài liệu 200 đoạn thành 200 vòng round-trip.
    batch_size: int = 64

    # Trần thời gian cho một lần gọi API embedding (giây).
    timeout_seconds: float = 30.0

    # Số lần thử lại khi API lỗi tạm thời (429, 5xx).
    max_retries: int = 3
