"""Cấu hình Domain Copilot: pgvector knowledge base + LLM provider."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class LlmConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_")

    database_url: str = "postgresql://postgres:CaVN2004@localhost:5434/iplms_knowledge"

    # Dùng chung cho cả embedding lẫn sinh câu trả lời — một tài khoản OpenAI.
    # Các tham số riêng của embedding (model, số chiều, lô) ở `embedding_config.py`.
    llm_api_key: str = ""

    # Model sinh câu trả lời. Cấu hình bằng env để có thể đổi model/alias mà
    # không phải build lại image. Luna phù hợp đường chat có lưu lượng cao;
    # production vẫn có thể ghim snapshot nếu cần tính tất định cao hơn.
    llm_model: str = "gpt-5.6-luna"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    llm_max_output_tokens: int = 1200

    # Retrieval là cấu hình của Copilot, không phải của model embedding.
    rag_top_k: int = 5
    rag_min_similarity: float = 0.35
