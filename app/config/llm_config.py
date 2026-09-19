"""Cấu hình Domain Copilot: pgvector knowledge base + LLM provider."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class LlmConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/iplms_db"

    # Dùng chung cho cả embedding lẫn sinh câu trả lời — một tài khoản OpenAI.
    # Các tham số riêng của embedding (model, số chiều, lô) ở `embedding_config.py`.
    llm_api_key: str = ""
