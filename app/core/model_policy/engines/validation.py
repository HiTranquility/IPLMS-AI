"""Validate model profiles before persistence and provider calls."""
import re

from app.core.model_policy.dtos import ModelProfileDraft

TASKS = ("copilot_answer", "test_generation", "test_judge")


def clean_profile(raw: dict) -> ModelProfileDraft:
    task = str(raw.get("task", ""))
    provider = str(raw.get("provider", ""))
    model = str(raw.get("model", "")).strip()
    effort = str(raw.get("reasoning_effort", "none"))
    output = int(raw.get("max_output_tokens", 1200))
    timeout = int(raw.get("timeout_seconds", 60))
    if task not in TASKS:
        raise ValueError("Tác vụ AI không hợp lệ.")
    if provider not in ("openai", "ollama"):
        raise ValueError("Provider chỉ hỗ trợ OpenAI hoặc Ollama.")
    if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,120}", model):
        raise ValueError("Model ID không hợp lệ.")
    if effort not in ("none", "low", "medium", "high"):
        raise ValueError("Mức reasoning không hợp lệ.")
    if provider == "ollama" and effort != "none":
        raise ValueError("Hồ sơ Ollama hiện chưa hỗ trợ cấu hình reasoning.")
    if not 100 <= output <= 8000 or not 5 <= timeout <= 180:
        raise ValueError("Giới hạn output hoặc timeout ngoài phạm vi cho phép.")
    return {
        "task": task, "provider": provider, "model": model,
        "reasoning_effort": effort, "max_output_tokens": output,
        "timeout_seconds": timeout,
    }
