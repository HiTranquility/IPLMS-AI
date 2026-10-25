"""Standard test and development fixtures for the dispute workflow contract.

Provides structured, authorized evidence bundles and in-memory mock adapters
conforming to the backend contract agreed with the platform team.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.copilot.engines.dispute_workflow.dependencies import (
    DisputeWorkflowDependencies,
    EvidenceAnalyzer,
    EvidenceClient,
    PolicyRetriever,
    RecommendationWriter,
)
from app.core.copilot.engines.dispute_workflow.state import DisputeWorkflowState
from app.core.exceptions import WorkflowStateError


STANDARD_BACKEND_EVIDENCE_BUNDLE: Dict[str, Any] = {
    "version": "evidence-v3",
    "parking_lot_id": "lot-downtown-01",
    "session": {
        "id": "session-202610-8842",
        "license_plate": "51A-99999",
        "vehicle_type": "car",
        "fee": 60000,
        "check_in_at": "2026-10-24T08:00:00Z",
        "check_out_at": "2026-10-24T10:30:00Z",
    },
    "media_refs": [
        {"provider": "s3", "key": "in-20261024-080000.jpg", "bucket": "parking-evidence"},
        {"provider": "s3", "key": "out-20261024-103000.jpg", "bucket": "parking-evidence"},
    ],
    "gate_events": [
        {
            "barrier_id": "barrier-out-01",
            "event": "SENSOR_TIMEOUT_DETECTED",
            "sensor_delay_minutes": 25.0,
            "timestamp": "2026-10-24T10:05:00Z",
        }
    ],
}


class ContractEvidenceClient:
    """In-memory evidence provider backed by contract-compliant bundles."""

    def __init__(self, bundles: Dict[str, Dict[str, Any]] | None = None):
        self._bundles = bundles or {
            "bundle-default": STANDARD_BACKEND_EVIDENCE_BUNDLE,
            "bundle-contract-001": STANDARD_BACKEND_EVIDENCE_BUNDLE,
        }

    async def load_bundle(self, evidence_bundle_id: str) -> Dict[str, Any]:
        bundle = self._bundles.get(evidence_bundle_id)
        if not bundle:
            # Fallback to standard bundle if matching prefix or id is given
            if evidence_bundle_id.startswith("bundle-"):
                bundle = dict(STANDARD_BACKEND_EVIDENCE_BUNDLE)
                bundle["session"] = dict(STANDARD_BACKEND_EVIDENCE_BUNDLE["session"])
                bundle["session"]["id"] = f"session-for-{evidence_bundle_id}"
                return bundle
            raise WorkflowStateError(f"Evidence bundle không tồn tại: {evidence_bundle_id}")
        return bundle


class ContractEvidenceAnalyzer:
    """Mock visual and sensor analyzer for barrier delay verification."""

    async def analyze(
        self,
        *,
        media_refs: List[Dict[str, Any]],
        session_snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        if len(media_refs) >= 2:
            findings.append({
                "kind": "plate_match",
                "matched": True,
                "confidence": 0.98,
                "model_version": "yolov8-plate-v2",
            })
            findings.append({
                "kind": "barrier_anomaly",
                "anomaly_detected": True,
                "sensor_delay_minutes": 25.0,
                "barrier_event": "SENSOR_TIMEOUT_DETECTED",
            })
        return findings


class ContractPolicyRetriever:
    """Mock policy retriever backed by simulated knowledge base chunks."""

    async def retrieve(
        self,
        *,
        query: str,
        parking_lot_id: str,
    ) -> List[Dict[str, Any]]:
        return [
            {
                "chunk_id": "policy-dispute-dieu-5",
                "source": "quy-che-khieu-nai-dieu-5.pdf",
                "content": "Điều 5: Sự cố barie hoặc sensor trễ trên 15 phút được miễn trừ phí thời gian chờ.",
                "similarity": 0.94,
            }
        ]


class ContractRecommendationWriter:
    """Deterministic recommendation writer obeying guardrails (ADR-0029)."""

    async def draft(self, state: DisputeWorkflowState) -> Dict[str, Any]:
        claimed = float(state.get("claimed_amount", 0.0))
        fee = float(state.get("session_snapshot", {}).get("fee", 0.0))
        refund_amount = min(claimed, fee) if fee > 0 else 0.0

        return {
            "verdict": "PARTIAL_REFUND" if refund_amount < fee else "APPROVE_REFUND",
            "recommended_refund": refund_amount,
            "justification": f"Xác nhận trễ barie đối chiếu theo Điều 5. Đề xuất hoàn {refund_amount:,.0f} VNĐ.",
            "cited_sources": ["quy-che-khieu-nai-dieu-5.pdf"],
        }


def create_contract_dispute_dependencies(
    *,
    bundles: Dict[str, Dict[str, Any]] | None = None,
) -> DisputeWorkflowDependencies:
    """Factory returning workflow dependencies configured with contract mock adapters."""
    return DisputeWorkflowDependencies(
        evidence_client=ContractEvidenceClient(bundles=bundles),
        evidence_analyzer=ContractEvidenceAnalyzer(),
        policy_retriever=ContractPolicyRetriever(),
        recommendation_writer=ContractRecommendationWriter(),
    )
