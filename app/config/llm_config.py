"""Cấu hình Domain Copilot: pgvector knowledge base + LLM provider."""
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class LlmConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_")

    database_url: str = "postgresql://postgres:***REMOVED***@localhost:5434/iplms_knowledge"

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

    # ── Local LLM (llama.cpp CUDA server: Qwen3.5-4B-Q4_K_M) ───────────────────
    # Provider: "local" (mặc định dùng llama-server CUDA), hoặc "openai"
    llm_provider: str = "local"
    local_llm_url: str = "http://127.0.0.1:8005/v1"
    local_llm_binary_path: str = "var/bin/llama/llama-server.exe"
    local_llm_model_path: str = "model/checkpoint/llm/Qwen3.5-4B-Q4_K_M.gguf"
    local_llm_port: int = 8005
    local_llm_host: str = "127.0.0.1"
    local_llm_gpu_layers: int = 33  # 100% full offload toàn bộ 33 layers lên GPU NVIDIA GTX 1650
    local_llm_ctx_size: int = 4096
    local_llm_parallel_slots: int = 1  # -np 1: Single slot KV cache (~270MB), dành toàn bộ VRAM cho weights & ANPR
    local_llm_threads: int = 4

