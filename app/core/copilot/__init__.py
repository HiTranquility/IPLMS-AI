"""Domain Copilot — RAG pipeline, trợ lý AI bãi đỗ xe (Pipeline 2)."""
from app.core.copilot.dtos.copilot_dto import (
    AnswerChunk,
    AskQuestionRequest,
    CopilotAnswer,
    DisputeArbitrationRequest,
    DisputeVerdict,
    UsageDay,
    UsageSummary,
    tuning_kwargs,
)
from app.core.copilot.guardrails.pii_redactor import redact
from app.core.copilot.services.copilot_service import CopilotService, copilot_service
from app.core.copilot.services.usage_service import CopilotUsageService, usage_service

copilot_usage_service = usage_service

__all__ = [
    "AnswerChunk",
    "AskQuestionRequest",
    "CopilotAnswer",
    "CopilotService",
    "CopilotUsageService",
    "DisputeArbitrationRequest",
    "DisputeVerdict",
    "UsageDay",
    "UsageSummary",
    "copilot_service",
    "copilot_usage_service",
    "redact",
    "tuning_kwargs",
    "usage_service",
]
