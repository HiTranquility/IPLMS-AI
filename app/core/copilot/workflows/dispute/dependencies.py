"""Ports used by dispute workflow nodes.

Production adapters are intentionally outside the graph. The backend must
authorize an evidence bundle before the graph can read it, and no dependency
exposes raw SQL or a payment/refund operation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.copilot.workflows.dispute.state import DisputeWorkflowState


class EvidenceClient(Protocol):
    async def load_bundle(self, evidence_bundle_id: str) -> dict[str, Any]: ...


class EvidenceAnalyzer(Protocol):
    async def analyze(
        self,
        *,
        media_refs: list[dict[str, Any]],
        session_snapshot: dict[str, Any],
    ) -> list[dict[str, Any]]: ...


class PolicyRetriever(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        parking_lot_id: str,
    ) -> list[dict[str, Any]]: ...


class RecommendationWriter(Protocol):
    """LLM soạn nháp. `claim_reason` là lời member — đưa vào prompt như dữ liệu,
    không như chỉ dẫn. Trả JSON schema {verdict, recommended_refund, justification,
    cited_sources}; node `draft_recommendation` kiểm lại bằng `validate_recommendation`."""

    async def draft(self, state: DisputeWorkflowState) -> dict[str, Any]: ...


@dataclass(frozen=True)
class DisputeWorkflowDependencies:
    evidence_client: EvidenceClient
    evidence_analyzer: EvidenceAnalyzer
    policy_retriever: PolicyRetriever
    recommendation_writer: RecommendationWriter
