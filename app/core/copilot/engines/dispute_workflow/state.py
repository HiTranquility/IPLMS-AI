"""Serializable state contract for the dispute graph."""
from __future__ import annotations

from typing import Any, Literal, TypedDict

from app.core.exceptions import WorkflowStateError


SCHEMA_VERSION = 1

WorkflowStatus = Literal[
    "created",
    "evidence_loaded",
    "evidence_analyzed",
    "policy_retrieved",
    "evidence_validated",
    "evidence_incomplete",
    "recommendation_drafted",
    "awaiting_review",
    "review_approved",
    "rejected",
    "approved_for_backend",
]


class ReviewDecision(TypedDict):
    action: Literal["approve", "reject"]
    reviewer_id: str
    comment: str


class DisputeWorkflowState(TypedDict, total=False):
    schema_version: int
    workflow_id: str
    dispute_id: str
    evidence_bundle_id: str
    actor_id: str
    parking_lot_id: str
    claim_reason: str
    claimed_amount: float
    evidence_version: str
    session_snapshot: dict[str, Any]
    media_refs: list[dict[str, Any]]
    vision_findings: list[dict[str, Any]]
    policy_chunks: list[dict[str, Any]]
    missing_evidence: list[str]
    recommendation: dict[str, Any]
    review: ReviewDecision
    approved_command: dict[str, Any]
    status: WorkflowStatus
    errors: list[dict[str, str]]


def _required_text(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise WorkflowStateError(f"{name} không được để trống.")
    return normalized


def make_initial_state(
    *,
    workflow_id: str,
    dispute_id: str,
    evidence_bundle_id: str,
    actor_id: str,
    claim_reason: str,
    claimed_amount: float,
) -> DisputeWorkflowState:
    if claimed_amount < 0:
        raise WorkflowStateError("claimed_amount không được âm.")
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": _required_text("workflow_id", workflow_id),
        "dispute_id": _required_text("dispute_id", dispute_id),
        "evidence_bundle_id": _required_text("evidence_bundle_id", evidence_bundle_id),
        "actor_id": _required_text("actor_id", actor_id),
        "claim_reason": _required_text("claim_reason", claim_reason),
        "claimed_amount": float(claimed_amount),
        "media_refs": [],
        "vision_findings": [],
        "policy_chunks": [],
        "missing_evidence": [],
        "errors": [],
        "status": "created",
    }


def validate_review(value: Any) -> ReviewDecision:
    if not isinstance(value, dict):
        raise WorkflowStateError("Quyết định review phải là object.")
    action = value.get("action")
    if action not in {"approve", "reject"}:
        raise WorkflowStateError("Review action chỉ nhận approve hoặc reject.")
    reviewer_id = _required_text("reviewer_id", str(value.get("reviewer_id") or ""))
    return {
        "action": action,
        "reviewer_id": reviewer_id,
        "comment": str(value.get("comment") or "").strip(),
    }


def assert_json_safe(value: Any, *, path: str = "state") -> None:
    """Reject bytes/secrets-shaped values before they enter a checkpoint."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise WorkflowStateError(f"{path} không được chứa bytes.")
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            assert_json_safe(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).lower()
            if normalized_key in {"access_token", "refresh_token", "signed_url"}:
                raise WorkflowStateError(f"{path}.{key} là trường bị cấm trong checkpoint.")
            assert_json_safe(item, path=f"{path}.{key}")
        return
    raise WorkflowStateError(f"{path} chứa kiểu không JSON-safe: {type(value).__name__}.")
