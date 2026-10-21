"""Cấu hình bộ test Knowledge Base (ISSUE-009): trần chi phí + ngưỡng cổng xuất bản."""
from pydantic import Field
from pydantic_settings import SettingsConfigDict

from app.config.base_config import BaseConfig


class EvalConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="AI_EVAL_")

    # Trần chi phí (SUGGESTION-009 R7): mỗi câu = 1 truy xuất + 1 lời gọi LLM
    # (+ 1 lời gọi judge với câu diễn giải).
    max_cases_per_run: int = Field(default=30, ge=1, le=200)
    max_concurrent_runs: int = Field(default=3, ge=1, le=20)
    max_generated_cases: int = Field(default=20, ge=1, le=50)

    # Ngưỡng cổng xuất bản (R4) — đã chốt 2026-09-25, không có đường bỏ qua.
    min_cases: int = Field(default=5, ge=1)
    min_pass_ratio: float = Field(default=0.9, ge=0.0, le=1.0)

    # Lượt chạy không cập nhật nhịp tim quá lâu = replica chạy nó đã chết.
    stale_after_seconds: int = Field(default=180, ge=30)

    # LLM-as-judge cho câu diễn giải; rỗng = dùng AI_LLM_MODEL.
    judge_model: str = ""
    judge_enabled: bool = True
