"""Cấu hình Domain Copilot: pgvector knowledge base + LLM provider."""
import os
from pathlib import Path
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig

# Model mặc định cho provider local/ollama (vừa VRAM GTX 1650 4 GB) — một nguồn (A-40).
DEFAULT_LOCAL_LLM_MODEL = "qwen2.5:0.5b"
# Tên chỉ có nghĩa với OpenAI hoặc với llama-server; gửi cho Ollama sẽ lỗi "model not found".
NON_OLLAMA_MODEL_NAMES = frozenset({"gpt-5.6-luna", "Qwen3.5-4B-Q4_K_M"})


class LlmConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_")

    database_url: str = ""

    # Dùng chung cho cả embedding lẫn sinh câu trả lời — một tài khoản OpenAI.
    # Các tham số riêng của embedding (model, số chiều, lô) ở `embedding_config.py`.
    llm_api_key: str = ""

    # ISSUE-011: endpoint tương thích OpenAI khác (vd Ollama chạy trên máy dev:
    # http://host.docker.internal:11434/v1 khi ai chạy trong Docker). Rỗng = OpenAI.
    # Có base_url mà không có key → dùng key giả "ollama" (Ollama bỏ qua key).
    llm_base_url: str = ""

    # Model sinh câu trả lời. Cấu hình bằng env hoặc runtime settings.
    # Mặc định dùng qwen2.5:0.5b khi dùng Ollama local (nhẹ, nhanh, không tràn VRAM GTX 1650).
    llm_model: str = DEFAULT_LOCAL_LLM_MODEL
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    llm_max_output_tokens: int = 1200

    # Retrieval là cấu hình của Copilot, không phải của model embedding.
    rag_top_k: int = 5
    rag_min_similarity: float = 0.35

    # ── Local LLM (Ollama hoặc llama.cpp server) ───────────────────────────────
    # Provider: "ollama", "local" (llama-server), hoặc "openai"
    llm_provider: str = "ollama"
    ollama_url: str = "http://127.0.0.1:11434/v1"
    local_llm_url: str = "http://127.0.0.1:8005/v1"
    local_llm_binary_path: str = "var/bin/llama/llama-server.exe"
    local_llm_model_path: str = "model/checkpoint/llm/Qwen3.5-4B-Q4_K_M.gguf"
    local_llm_port: int = 8005
    local_llm_host: str = "127.0.0.1"
    local_llm_gpu_layers: int = 33
    local_llm_ctx_size: int = 4096
    local_llm_parallel_slots: int = 1
    local_llm_threads: int = 4

    @property
    def active_model_name(self) -> str:
        """Tên model đang cấu hình (`llm_model`); local/ollama không nhận tên OpenAI/GGUF.

        Khi llama-server thật sự đang chạy, factory dùng `local_gguf_model_name` thay vào.
        """
        if self.llm_provider in ("local", "ollama") and (not self.llm_model or self.llm_model in NON_OLLAMA_MODEL_NAMES):
            return DEFAULT_LOCAL_LLM_MODEL
        return self.llm_model or DEFAULT_LOCAL_LLM_MODEL

    @property
    def local_gguf_model_name(self) -> str | None:
        """Tên file GGUF llama-server nạp, None nếu chưa có file."""
        path = Path(self.local_llm_model_path) if self.local_llm_model_path else None
        return path.stem if path and path.is_file() else None
