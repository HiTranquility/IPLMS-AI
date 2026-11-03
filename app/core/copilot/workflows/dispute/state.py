"""Serializable state contract for the dispute graph."""
from __future__ import annotations

import math
from typing import Any, Literal, TypedDict

from app.core.copilot.guardrails.output_guard import violation as output_guard_violation
from app.core.exceptions import WorkflowStateError


SCHEMA_VERSION = 1
# Lý do khiếu nại do member viết: đầu vào độc hại mặc định (ADR-0029 luật 2).
MAX_CLAIM_REASON_CHARS = 2000
MAX_JUSTIFICATION_CHARS = 1000
# Khớp 3 giá trị `ArbitrationVerdict` trong copilot_service.proto cộng MANUAL_REVIEW
# (trạng thái nội bộ workflow khi LLM không đủ căn cứ, cần người duyệt quyết).
VERDICTS = ("APPROVE_REFUND", "PARTIAL_REFUND", "REJECT", "MANUAL_REVIEW")

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


def _is_finite_non_negative_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value)) and float(value) >= 0.0


def make_initial_state(
    *,
    workflow_id: str,
    dispute_id: str,
    evidence_bundle_id: str,
    actor_id: str,
    claim_reason: str,
    claimed_amount: float,
) -> DisputeWorkflowState:
    if not _is_finite_non_negative_number(claimed_amount):
        raise WorkflowStateError("claimed_amount phải là số hữu hạn không âm.")
    if len(claim_reason) > MAX_CLAIM_REASON_CHARS:
        raise WorkflowStateError(f"claim_reason tối đa {MAX_CLAIM_REASON_CHARS} ký tự.")
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


def validate_recommendation(
    value: Any,
    *,
    claimed_amount: float,
    session_fee: Any,
    sources: list[str],
    context_text: str = "",
) -> dict[str, Any]:
    """Đề xuất của LLM chỉ là dữ liệu: kiểm tất định trước khi tới người duyệt (ADR-0029 luật 1, 3).

    Kết luận là enum; số tiền bị chặn bởi CODE — không quá số tiền đòi, không quá
    phí thật của phiên (số tiền đòi do member tự khai). Nguồn trích phải là đoạn
    quy chế đã truy xuất. Sai bất kỳ điểm nào thì dừng, không "sửa giúp".
    """
    if not isinstance(value, dict):
        raise WorkflowStateError("Đề xuất phải là object.")
    expected = {"verdict", "recommended_refund", "justification", "cited_sources"}
    if set(value) != expected:
        raise WorkflowStateError(f"Đề xuất phải có đúng các khoá {sorted(expected)}.")
    verdict = value["verdict"]
    if verdict not in VERDICTS:
        raise WorkflowStateError(f"verdict chỉ nhận {', '.join(VERDICTS)}.")
    if not _is_finite_non_negative_number(claimed_amount):
        raise WorkflowStateError("claimed_amount phải là số hữu hạn không âm.")
    refund = value["recommended_refund"]
    if not _is_finite_non_negative_number(refund):
        raise WorkflowStateError("recommended_refund phải là số không âm.")
    if refund > 0:
        if not _is_finite_non_negative_number(session_fee):
            raise WorkflowStateError("Phiên đỗ không có phí hợp lệ nên không đề xuất hoàn tiền được.")
        cap = min(float(claimed_amount), float(session_fee))
        if refund > cap:
            raise WorkflowStateError(f"recommended_refund vượt trần {cap:,.0f} (min số tiền đòi, phí phiên).")
    if verdict in {"REJECT", "MANUAL_REVIEW"} and refund != 0:
        raise WorkflowStateError(f"{verdict} thì recommended_refund phải bằng 0.")
    if verdict in {"APPROVE_REFUND", "PARTIAL_REFUND"} and refund == 0:
        raise WorkflowStateError(f"{verdict} thì recommended_refund phải lớn hơn 0.")
    justification = value["justification"]
    if not isinstance(justification, str) or not justification.strip():
        raise WorkflowStateError("justification không được để trống.")
    if len(justification) > MAX_JUSTIFICATION_CHARS:
        raise WorkflowStateError(f"justification tối đa {MAX_JUSTIFICATION_CHARS} ký tự.")
    guard_rule = output_guard_violation(justification, context_text)
    if guard_rule:
        raise WorkflowStateError(f"justification vi phạm output guard ({guard_rule}).")
    cited = value["cited_sources"]
    if not isinstance(cited, list) or any(source not in sources for source in cited):
        raise WorkflowStateError("cited_sources chỉ được trích quy chế đã truy xuất.")
    return {
        "verdict": verdict,
        "recommended_refund": refund,
        "justification": justification.strip(),
        "cited_sources": list(dict.fromkeys(cited)),
    }


def assert_json_safe(value: Any, *, path: str = "state") -> None:
    """Reject bytes/secrets-shaped/non-finite values before they enter a checkpoint."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise WorkflowStateError(f"{path} không được chứa bytes.")
    if isinstance(value, float) and not math.isfinite(value):
        raise WorkflowStateError(f"{path} không được chứa NaN/Infinity.")
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
