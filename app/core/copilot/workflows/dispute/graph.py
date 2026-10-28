"""LangGraph topology for a bounded dispute recommendation workflow."""
from __future__ import annotations

from typing import Any

from app.core.copilot.workflows.dispute.dependencies import (
    DisputeWorkflowDependencies,
)
from app.core.copilot.workflows.dispute.nodes import (
    finalize,
    make_analyze_evidence_node,
    make_draft_recommendation_node,
    make_load_evidence_node,
    make_retrieve_policy_node,
    prepare_human_review,
    request_human_review,
    route_after_review,
    route_after_validation,
    validate_evidence,
)
from app.core.copilot.workflows.dispute.state import DisputeWorkflowState
from app.core.exceptions import WorkflowConfigurationError


def build_dispute_graph(
    dependencies: DisputeWorkflowDependencies,
    *,
    checkpointer: Any = None,
) -> Any:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise WorkflowConfigurationError(
            "Thiếu package langgraph; workflow dispute chưa thể khởi động."
        ) from exc

    builder = StateGraph(DisputeWorkflowState)
    builder.add_node("load_evidence", make_load_evidence_node(dependencies))
    builder.add_node("analyze_evidence", make_analyze_evidence_node(dependencies))
    builder.add_node("retrieve_policy", make_retrieve_policy_node(dependencies))
    builder.add_node("validate_evidence", validate_evidence)
    builder.add_node("draft_recommendation", make_draft_recommendation_node(dependencies))
    builder.add_node("prepare_human_review", prepare_human_review)
    builder.add_node("human_review", request_human_review)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "load_evidence")
    builder.add_edge("load_evidence", "analyze_evidence")
    builder.add_edge("analyze_evidence", "retrieve_policy")
    builder.add_edge("retrieve_policy", "validate_evidence")
    builder.add_conditional_edges(
        "validate_evidence",
        route_after_validation,
        {"draft": "draft_recommendation", "review": "prepare_human_review"},
    )
    builder.add_edge("draft_recommendation", "prepare_human_review")
    builder.add_edge("prepare_human_review", "human_review")
    builder.add_conditional_edges(
        "human_review",
        route_after_review,
        {"finalize": "finalize", "end": END},
    )
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)
