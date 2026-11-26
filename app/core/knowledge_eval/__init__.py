"""Domain Knowledge Eval — bộ test + cổng xuất bản Knowledge Base (ISSUE-009)."""
from typing import Any

from app.core.knowledge_eval.dtos import (
    EvalScopeDto,
    ScopeReadinessDto,
    TestCaseDto,
    TestRunResultDto,
    TestRunSummaryDto,
)

__all__ = [
    "EvalScopeDto",
    "EvalService",
    "ScopeReadinessDto",
    "TestCaseDto",
    "TestRunResultDto",
    "TestRunSummaryDto",
    "eval_service",
]


def __getattr__(name: str) -> Any:
    if name in ("EvalService", "eval_service"):
        from app.core.knowledge_eval.services import eval_service as _mod

        return getattr(_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
