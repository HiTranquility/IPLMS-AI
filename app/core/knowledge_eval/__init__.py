"""Domain Knowledge Eval — bộ test + cổng xuất bản Knowledge Base (ISSUE-009)."""
from app.core.knowledge_eval.dtos import (
    EvalScopeDto,
    ScopeReadinessDto,
    TestCaseDto,
    TestRunResultDto,
    TestRunSummaryDto,
)

__all__ = [
    "EvalScopeDto",
    "KnowledgeEvalService",
    "ScopeReadinessDto",
    "TestCaseDto",
    "TestRunResultDto",
    "TestRunSummaryDto",
    "knowledge_eval_service",
]


def __getattr__(name: str):
    if name in ("KnowledgeEvalService", "knowledge_eval_service"):
        from app.core.knowledge_eval import services

        return getattr(services, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
