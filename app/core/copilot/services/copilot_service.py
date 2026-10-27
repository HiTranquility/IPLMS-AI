"""Nghiệp vụ Trợ lý Hỏi Đáp RAG & Trọng Tài Tranh Chấp."""
import time
from typing import Any, AsyncGenerator, Dict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from app.config import get_config

from app.core.copilot.dtos.copilot_dto import (
    AnswerChunk,
    AskQuestionRequest,
    CopilotAnswer,
    DisputeArbitrationRequest,
    DisputeVerdict,
    tuning_kwargs,
)
from app.core.copilot.engines.dispute_workflow.fixtures import (
    STANDARD_BACKEND_EVIDENCE_BUNDLE,
    ContractEvidenceAnalyzer,
    ContractEvidenceClient,
    ContractPolicyRetriever,
    ContractRecommendationWriter,
    DisputeWorkflowDependencies,
)
from app.core.copilot.engines.dispute_workflow.graph import build_dispute_graph
from app.core.copilot.engines.dispute_workflow.state import make_initial_state
from app.core.copilot.engines.rag_pipeline import PROMPT_VERSION, rag_pipeline
from app.core.copilot.services.usage_service import usage_service
from app.core.exceptions import FeatureNotImplementedError
from app.infra.monitoring.ai_logger import ai_telemetry_logger
from app.util.logger import logger


class CopilotService:
    @staticmethod
    async def ask_question(request: AskQuestionRequest, task: str = "copilot_ask") -> CopilotAnswer:
        """Answer through the real embedding → pgvector → Responses pipeline.

        `task` khác `copilot_ask` (vd. `console_try`) để lượt thử nội bộ không vào số
        mức dùng sản phẩm (IPLMS ADR-0050 §3).
        """
        turn_id, started = str(uuid4()), time.monotonic()
        try:
            result = await rag_pipeline.query(
                request.query,
                parking_lot_id=request.parking_lot_id,
                preview=request.preview,
                **tuning_kwargs(request),
            )
        except Exception as exc:
            usage_service.record_soon(usage_service.build_entry(
                turn_id=turn_id, task=task, status="ERROR", started=started,
                request=request, error_code=type(exc).__name__,
            ))
            raise
        usage_service.record_soon(usage_service.build_entry(
            turn_id=turn_id, task=task, status=result["status"], started=started,
            request=request, result=result, answer=result["answer"],
        ))
        return CopilotAnswer(
            answer=result["answer"],
            sources=result["sources"],
            confidence=result["confidence"],
            model_revision=result.get("model_revision", ""),
            turn_id=turn_id,
            prompt_version=PROMPT_VERSION,
        )

    @staticmethod
    async def stream_answer(request: AskQuestionRequest) -> AsyncGenerator[AnswerChunk, None]:
        """Stream the same grounded pipeline without buffering the full answer."""
        turn_id, started = str(uuid4()), time.monotonic()
        try:
            async for chunk in rag_pipeline.stream_query(
                request.query,
                parking_lot_id=request.parking_lot_id,
                preview=getattr(request, "preview", False),
                **tuning_kwargs(request),
            ):
                finished = chunk["is_finished"]
                if finished:
                    usage_service.record_soon(usage_service.build_entry(
                        turn_id=turn_id, task="copilot_stream", status=chunk.get("status", "SUCCESS"),
                        started=started, request=request, result=chunk,
                        answer=chunk.get("answer", ""),
                    ))
                yield AnswerChunk(
                    token=chunk["token"],
                    is_finished=finished,
                    sources=chunk.get("sources", []),
                    citations=chunk.get("citations", []),
                    confidence=chunk.get("confidence"),
                    refused=chunk.get("refused", False),
                    guardrail_triggered=chunk.get("guardrail_triggered"),
                    model_revision=chunk.get("model_revision", ""),
                    turn_id=turn_id if finished else "",
                    prompt_version=chunk.get("prompt_version", PROMPT_VERSION if finished else ""),
                    latency_ms=chunk.get("latency_ms"),
                    input_tokens=chunk.get("input_tokens"),
                    output_tokens=chunk.get("output_tokens"),
                    speed_tok_s=chunk.get("speed_tok_s"),
                    context_tokens=chunk.get("context_tokens"),
                    context_limit=chunk.get("context_limit") or getattr(get_config().llm, "local_llm_ctx_size", 4096),
                )
        except Exception as exc:
            usage_service.record_soon(usage_service.build_entry(
                turn_id=turn_id, task="copilot_stream", status="ERROR", started=started,
                request=request, error_code=type(exc).__name__,
            ))
            raise

    @staticmethod
    async def arbitrate_dispute(request: DisputeArbitrationRequest) -> DisputeVerdict:
        """[NEVER] bật lại cho tới khi phần thẩm định phía sau là thật.

        Bản trước trả về phán quyết viết cứng: LUÔN ``APPROVE_REFUND``, hoàn đúng
        số tiền khách đòi, kèm lý do bịa về "barie quét vé chậm 15 phút" và một
        URL bằng chứng không tồn tại — bất kể khiếu nại là gì, phiên đỗ nào, có
        đúng sự thật hay không.

        Nó không tự chi tiền: ``dispute.service.ts::arbitrateWithAi`` chỉ trả DTO
        cho người xem. Nhưng nhân viên đọc được một "kết luận thẩm định" trông
        chính thức như vậy thì rất khó cãi lại, nên trên thực tế nó là cỗ máy
        sản xuất giấy đòi tiền theo yêu cầu.

        Thà báo UNIMPLEMENTED còn hơn trả một con số trông hợp lý: lỗi thì thấy
        ngay, còn số bịa thì không để lại dấu vết nào trong log lẫn metric.

        Việc thật cần làm trước khi mở lại: nạp log vào/ra + ảnh snapshot của
        phiên, đối chiếu với quy chế đã nạp qua RAG (xem SUGGESTION-008), rồi mới
        kết luận. RAG hỏi đáp đã là thật, nhưng nó không tự có evidence của một
        phiên đỗ cụ thể nên chưa đủ cơ sở để ra phán quyết tài chính.
        """
        logger.warning(
            f"CopilotService.ArbitrateDispute bị gọi cho dispute #{request.dispute_id} "
            f"— tính năng chưa triển khai, từ chối thay vì trả phán quyết bịa."
        )
        raise FeatureNotImplementedError(
            "Thẩm định tranh chấp bằng AI chưa khả dụng: phần đối chiếu quy chế và "
            "log phiên đỗ chưa được triển khai. Vui lòng xử lý khiếu nại thủ công."
        )

    @staticmethod
    def get_metrics_summary() -> Dict[str, Any]:
        """Tổng hợp telemetry AI requests, tokens, latency và chi phí."""
        return ai_telemetry_logger.get_metrics_summary()

    @staticmethod
    async def simulate_dispute_workflow(
        *,
        dispute_id: str,
        claim_reason: str,
        claimed_amount: float,
        has_checkin_snapshot: bool = True,
        has_checkout_snapshot: bool = True,
    ) -> Dict[str, Any]:
        """Chạy quy trình phân xử khiếu nại bằng LangGraph StateGraph thật (ai ISSUE-001)."""
        bundle = dict(STANDARD_BACKEND_EVIDENCE_BUNDLE)
        bundle["session"] = dict(STANDARD_BACKEND_EVIDENCE_BUNDLE["session"])
        bundle["session"]["fee"] = float(claimed_amount)
        media_refs = []
        if has_checkin_snapshot:
            media_refs.append({"provider": "s3", "key": "in-checkin.jpg", "bucket": "parking-evidence"})
        if has_checkout_snapshot:
            media_refs.append({"provider": "s3", "key": "out-checkout.jpg", "bucket": "parking-evidence"})
        bundle["media_refs"] = media_refs

        deps = DisputeWorkflowDependencies(
            evidence_client=ContractEvidenceClient(bundles={f"bundle-{dispute_id}": bundle}),
            evidence_analyzer=ContractEvidenceAnalyzer(),
            policy_retriever=ContractPolicyRetriever(),
            recommendation_writer=ContractRecommendationWriter(),
        )

        checkpointer = InMemorySaver()
        graph = build_dispute_graph(deps, checkpointer=checkpointer)

        initial_state = make_initial_state(
            workflow_id=f"wf-{dispute_id}",
            dispute_id=dispute_id,
            evidence_bundle_id=f"bundle-{dispute_id}",
            actor_id="console-operator",
            claim_reason=claim_reason or "Khiếu nại phí gửi xe",
            claimed_amount=claimed_amount,
        )

        config = {"configurable": {"thread_id": f"sim-{dispute_id}"}}
        result_state = await graph.ainvoke(initial_state, config)

        transitions = [
            {
                "step": 1,
                "node": "load_evidence",
                "status": "COMPLETED",
                "data": {
                    "dispute_id": dispute_id,
                    "evidence_version": result_state.get("evidence_version"),
                    "parking_lot_id": result_state.get("parking_lot_id"),
                    "media_count": len(result_state.get("media_refs", [])),
                },
                "description": "Nạp gói bằng chứng phiên đỗ (log vào, log ra, ảnh chụp camera barrier).",
            },
            {
                "step": 2,
                "node": "analyze_evidence",
                "status": "COMPLETED",
                "data": {
                    "vision_findings": result_state.get("vision_findings", []),
                },
                "description": "Trích xuất đặc trưng thị giác và timestamp đối chiếu sự cố barie.",
            },
            {
                "step": 3,
                "node": "retrieve_policy",
                "status": "COMPLETED",
                "data": {
                    "policy_chunks": result_state.get("policy_chunks", []),
                },
                "description": "Truy xuất quy định hoàn phí tương ứng từ kho tri thức pgvector.",
            },
            {
                "step": 4,
                "node": "validate_evidence",
                "status": "COMPLETED",
                "data": {
                    "missing_evidence": result_state.get("missing_evidence", []),
                    "is_valid": len(result_state.get("missing_evidence", [])) == 0,
                },
                "description": "Kiểm tra tính toàn vẹn của bằng chứng trước khi sinh đề xuất.",
            },
        ]

        if result_state.get("recommendation"):
            rec = result_state["recommendation"]
            transitions.append({
                "step": len(transitions) + 1,
                "node": "draft_recommendation",
                "status": "COMPLETED",
                "data": {
                    "proposed_verdict": rec.get("verdict"),
                    "recommended_amount": rec.get("recommended_refund"),
                    "justification": rec.get("justification"),
                    "cited_sources": rec.get("cited_sources", []),
                },
                "description": "Dự thảo phương án giải quyết dựa trên quy chế và bằng chứng.",
            })

        transitions.append({
            "step": len(transitions) + 1,
            "node": "human_review",
            "status": "AWAITING_STAFF_SIGN_OFF" if result_state.get("status") == "awaiting_review" else result_state.get("status"),
            "data": {
                "requires_human_approval": True,
                "assigned_role": "PARKING_LOT_SUPERVISOR",
                "auto_refund_permitted": False,
            },
            "description": "Chuyển giao cho Giám sát bãi xe ký duyệt (ngăn chặn AI tự ý chi trả tiền).",
        })

        return {
            "success": True,
            "dispute_id": dispute_id,
            "workflow": "LangGraph StateGraph [Bounded Dispute Recommendation]",
            "nodes_traversed": len(transitions),
            "steps": transitions,
            "final_status": "AWAITING_STAFF_SIGN_OFF" if result_state.get("status") == "awaiting_review" else result_state.get("status"),
        }


copilot_service = CopilotService()
