"""Small, auditable nodes for the dispute workflow."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.core.copilot.engines.dispute_workflow.dependencies import (
    DisputeWorkflowDependencies,
)
from app.core.copilot.engines.dispute_workflow.state import (
    DisputeWorkflowState,
    assert_json_safe,
    validate_recommendation,
    validate_review,
)
from app.core.knowledge.engines.injection_scan import find_instructions
from app.core.exceptions import WorkflowStateError


Node = Callable[[DisputeWorkflowState], Awaitable[dict[str, Any]]]


def _text(value: Any) -> str:
    return str(value or "").strip()


def make_load_evidence_node(deps: DisputeWorkflowDependencies) -> Node:
    async def load_evidence(state: DisputeWorkflowState) -> dict[str, Any]:
        bundle = await deps.evidence_client.load_bundle(state["evidence_bundle_id"])
        assert_json_safe(bundle, path="evidence_bundle")
        session = bundle.get("session")
        if not isinstance(session, dict):
            raise WorkflowStateError("Evidence bundle thiếu session snapshot.")
        media_refs = bundle.get("media_refs") or []
        if not isinstance(media_refs, list):
            raise WorkflowStateError("media_refs phải là một danh sách.")
        parking_lot_id = _text(bundle.get("parking_lot_id"))
        if not parking_lot_id:
            raise WorkflowStateError("Evidence bundle thiếu parking_lot_id đã authorize.")
        return {
            "evidence_version": _text(bundle.get("version")) or "unversioned",
            "parking_lot_id": parking_lot_id,
            "session_snapshot": session,
            "media_refs": media_refs,
            "status": "evidence_loaded",
        }

    return load_evidence


def make_analyze_evidence_node(deps: DisputeWorkflowDependencies) -> Node:
    async def analyze_evidence(state: DisputeWorkflowState) -> dict[str, Any]:
        findings = await deps.evidence_analyzer.analyze(
            media_refs=state.get("media_refs", []),
            session_snapshot=state["session_snapshot"],
        )
        assert_json_safe(findings, path="vision_findings")
        return {"vision_findings": findings, "status": "evidence_analyzed"}

    return analyze_evidence


def make_retrieve_policy_node(deps: DisputeWorkflowDependencies) -> Node:
    async def retrieve_policy(state: DisputeWorkflowState) -> dict[str, Any]:
        chunks = await deps.policy_retriever.retrieve(
            query=state["claim_reason"],
            parking_lot_id=state["parking_lot_id"],
        )
        assert_json_safe(chunks, path="policy_chunks")
        return {"policy_chunks": chunks, "status": "policy_retrieved"}

    return retrieve_policy


async def validate_evidence(state: DisputeWorkflowState) -> dict[str, Any]:
    missing: list[str] = []
    if not state.get("session_snapshot"):
        missing.append("session_snapshot")
    if len(state.get("media_refs", [])) < 2:
        missing.append("check_in_out_media")
    if not state.get("vision_findings"):
        missing.append("vision_findings")
    if not state.get("policy_chunks"):
        missing.append("applicable_policy")
    return {
        "missing_evidence": missing,
        "status": "evidence_incomplete" if missing else "evidence_validated",
    }


def route_after_validation(state: DisputeWorkflowState) -> str:
    return "review" if state.get("missing_evidence") else "draft"


def make_draft_recommendation_node(deps: DisputeWorkflowDependencies) -> Node:
    async def draft_recommendation(state: DisputeWorkflowState) -> dict[str, Any]:
        recommendation = await deps.recommendation_writer.draft(state)
        assert_json_safe(recommendation, path="recommendation")
        if not recommendation:
            raise WorkflowStateError("Recommendation writer trả kết quả rỗng.")
        recommendation = validate_recommendation(
            recommendation,
            claimed_amount=state["claimed_amount"],
            session_fee=state["session_snapshot"].get("fee"),
            sources=[c["source"] for c in state.get("policy_chunks", []) if c.get("source")],
        )
        return {
            "recommendation": recommendation,
            "status": "recommendation_drafted",
        }

    return draft_recommendation


def _review_payload(state: DisputeWorkflowState) -> dict[str, Any]:
    recommendation = state.get("recommendation") or {}
    return {
        "workflow_id": state["workflow_id"],
        "dispute_id": state["dispute_id"],
        "evidence_version": state.get("evidence_version"),
        "missing_evidence": state.get("missing_evidence", []),
        "recommendation": recommendation,
        "policy_sources": [
            chunk.get("source")
            for chunk in state.get("policy_chunks", [])
            if chunk.get("source")
        ],
        # Người duyệt cần biết khiếu nại có câu ra lệnh cho AI (ADR-0029 luật 2).
        "claim_injection_flags": find_instructions(state.get("claim_reason", "")),
        "question": "Duyệt, từ chối hoặc sửa đề xuất xử lý tranh chấp?",
    }


async def prepare_human_review(state: DisputeWorkflowState) -> dict[str, Any]:
    """Persist an explicit waiting status before the interrupt checkpoint."""
    return {"status": "awaiting_review"}


async def request_human_review(state: DisputeWorkflowState) -> dict[str, Any]:
    # Import locally so pure node/state tests do not require the optional graph runtime.
    try:
        from langgraph.types import interrupt
    except ImportError as exc:  # pragma: no cover - covered by graph dependency gate
        raise WorkflowStateError("Thiếu package langgraph để chạy human review.") from exc

    decision = validate_review(interrupt(_review_payload(state)))
    return {
        "review": decision,
        "status": "review_approved" if decision["action"] == "approve" else "rejected",
    }


def route_after_review(state: DisputeWorkflowState) -> str:
    return "finalize" if state.get("status") == "review_approved" else "end"


async def finalize(state: DisputeWorkflowState) -> dict[str, Any]:
    review = state.get("review")
    if not review or review["action"] != "approve":
        raise WorkflowStateError("Chỉ review đã approve mới được tạo backend command.")
    return {
        "approved_command": {
            "command": "REVIEW_DISPUTE_RECOMMENDATION",
            "workflow_id": state["workflow_id"],
            "dispute_id": state["dispute_id"],
            "evidence_version": state.get("evidence_version"),
            "reviewer_id": review["reviewer_id"],
            "operation_key": f"{state['workflow_id']}:approved-action:v1",
            "recommendation": state.get("recommendation"),
        },
        "status": "approved_for_backend",
    }
