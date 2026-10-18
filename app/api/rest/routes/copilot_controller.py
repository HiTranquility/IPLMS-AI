"""REST route cho Copilot (RAG hỏi đáp quy chế & quy trình tranh chấp)."""
import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.copilot.dtos.copilot_dto import (
    AskQuestionRequest,
    CopilotAnswer,
    DisputeArbitrationRequest,
)
from app.core.copilot.services.copilot_service import copilot_service
from app.core.exceptions import FeatureNotImplementedError
from app.api.rest.schemas.base_response import BaseResponse
from app.config import get_config

router = APIRouter(prefix="/copilot", tags=["Copilot & RAG"])

def get_seed_path() -> str:
    candidates = [
        os.path.join(os.getcwd(), "data", "knowledge", "regulations_seed.json"),
        os.path.join("/app", "data", "knowledge", "regulations_seed.json"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/knowledge/regulations_seed.json")),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


class AskPayload(BaseModel):
    query: str
    parking_lot_id: Optional[str] = None
    user_id: Optional[str] = "test-user"
    api_key_override: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    mode: str = "rag_pgvector"
    refused: bool = False
    guardrail_triggered: Optional[str] = None
    prompt_version: str = "v2"
    latency_ms: Optional[float] = None


class DisputePayload(BaseModel):
    dispute_id: str = "DSP-1002"
    session_id: str = "sess-8891"
    claim_reason: str = "Barie không tự động mở, bị tính thêm phí trễ giờ"
    claimed_amount: float = 35000.0


class WorkflowSimulationPayload(BaseModel):
    dispute_id: str = "DSP-1002"
    claim_reason: str = "Barie kẹt lúc ra cổng > 15 phút"
    claimed_amount: float = 35000.0
    has_checkin_snapshot: bool = True
    has_checkout_snapshot: bool = True


@router.get("/metrics")
async def get_ai_metrics():
    """Lấy số liệu thống kê AI requests, tokens, latency và chi phí (Mục 4.2)."""
    from app.infra.monitoring.ai_logger import ai_telemetry_logger
    return BaseResponse.ok([ai_telemetry_logger.get_metrics_summary()], "AI Telemetry & Cost Summary")


def _stream_sse_response(
    query: str,
    parking_lot_id: Optional[str] = None,
    user_id: str = "test-user",
) -> StreamingResponse:
    req = AskQuestionRequest(
        query=query,
        parking_lot_id=parking_lot_id or None,
        user_id=user_id,
    )

    async def event_generator():
        try:
            async for chunk in copilot_service.stream_answer(req):
                payload = {
                    "token": chunk.token,
                    "is_finished": chunk.is_finished,
                    "sources": chunk.sources,
                    "confidence": chunk.confidence,
                    "refused": chunk.refused,
                    "guardrail_triggered": chunk.guardrail_triggered,
                    "prompt_version": chunk.prompt_version,
                    "latency_ms": chunk.latency_ms,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            err_payload = {
                "token": f"\n\n[Lỗi streaming: {str(exc)}]",
                "is_finished": True,
                "sources": [],
                "confidence": 0.0,
                "refused": False,
                "guardrail_triggered": "STREAM_EXCEPTION",
                "prompt_version": "v2",
                "latency_ms": 0.0,
            }
            yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream")
def stream_copilot_post(payload: AskPayload):
    """Stream câu trả lời AI theo từng token thời gian thực bằng Server-Sent Events (SSE)."""
    return _stream_sse_response(
        query=payload.query,
        parking_lot_id=payload.parking_lot_id,
        user_id=payload.user_id or "test-user",
    )


@router.get("/stream")
def stream_copilot_get(
    query: str,
    parking_lot_id: Optional[str] = None,
    user_id: Optional[str] = "test-user",
):
    """Stream SSE qua GET request (tương thích EventSource trình duyệt chuẩn)."""
    return _stream_sse_response(
        query=query,
        parking_lot_id=parking_lot_id,
        user_id=user_id or "test-user",
    )


@router.post("/ask", response_model=BaseResponse[AskResponse])
async def ask_copilot(payload: AskPayload) -> BaseResponse[AskResponse]:
    """Hỏi đáp quy chế bãi xe thông qua RAG pipeline."""
    cfg = get_config()
    api_key = payload.api_key_override or cfg.llm.llm_api_key

    # Nếu có API key hoặc dùng LLM nội bộ (local llama-server), chạy pipeline RAG chuẩn
    is_local = (cfg.llm.llm_provider == "local")
    if api_key or is_local:
        try:
            req = AskQuestionRequest(
                query=payload.query,
                parking_lot_id=payload.parking_lot_id or None,
                user_id=payload.user_id or "test-user",
            )
            ans: CopilotAnswer = await copilot_service.ask_question(req)
            return BaseResponse.ok(
                [AskResponse(
                    answer=ans.answer,
                    sources=ans.sources,
                    confidence=ans.confidence,
                    mode="rag_local" if is_local else "rag_live",
                    refused=ans.refused,
                    guardrail_triggered=ans.guardrail_triggered,
                    prompt_version=ans.prompt_version,
                    latency_ms=ans.latency_ms,
                )],
                "Answer generated via local RAG" if is_local else "Answer generated via live RAG"
            )
        except Exception as exc:
            pass  # Fallback to local semantic seed lookup if LLM failed

    # Offline fallback qua seed documents trong data/knowledge/
    seed_path = get_seed_path()
    if os.path.exists(seed_path):
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                seeds = json.load(f)
            
            q_lower = payload.query.lower()
            matched_sources = []
            matched_snippets = []
            
            for item in seeds:
                content = item.get("content", "")
                title = item.get("title", "")
                source = item.get("source", "regulations_seed.json")
                category = item.get("category", "general")
                
                # Simple keyword matching across query tokens
                tokens = [t for t in q_lower.split() if len(t) > 2]
                match_count = sum(1 for t in tokens if t in content.lower() or t in title.lower())
                
                if match_count > 0 or not tokens:
                    matched_sources.append(source)
                    matched_snippets.append(f"**{title}** ({category}):\n{content}")
                    if len(matched_snippets) >= 2:
                        break

            if matched_snippets:
                answer = "🔍 **[Tra cứu từ Kho Tri Thức Nội Bộ]**:\n\n" + "\n\n---\n\n".join(matched_snippets)
                return BaseResponse.ok(
                    [AskResponse(answer=answer, sources=list(set(matched_sources)), confidence=0.88, mode="local_knowledge_seed")],
                    "Grounded answer from local knowledge base"
                )
        except Exception as exc:
            return BaseResponse.fail(f"Knowledge lookup error: {exc}")

    return BaseResponse.ok(
        [AskResponse(
            answer="Chưa tìm thấy điều khoản phù hợp trong kho tri thức hoặc chưa cấu hình AI_LLM_API_KEY.",
            sources=[],
            confidence=0.0,
            mode="no_context"
        )],
        "No context found"
    )


@router.post("/arbitrate-dispute")
async def arbitrate_dispute(payload: DisputePayload) -> Dict[str, Any]:
    """Kiểm tra chức năng Trọng tài tranh chấp (tuân thủ luật Thà lỗi hơn bịa)."""
    try:
        req = DisputeArbitrationRequest(
            dispute_id=payload.dispute_id,
            session_id=payload.session_id,
            claim_reason=payload.claim_reason,
            claimed_amount=payload.claimed_amount,
        )
        await copilot_service.arbitrate_dispute(req)
        return {"success": True, "verdict": "UNEXPECTED_APPROVED"}
    except FeatureNotImplementedError as exc:
        return {
            "success": False,
            "status": "UNIMPLEMENTED",
            "message": str(exc),
            "safety_rule": "Thà lỗi hơn bịa (ADR-0008): Hệ thống từ chối tự động hoàn tiền khi chưa có model đối chiếu video log và quy chế thật.",
        }
    except Exception as exc:
        return {"success": False, "status": "ERROR", "message": str(exc)}


@router.post("/dispute-workflow/simulate")
async def simulate_dispute_workflow(payload: WorkflowSimulationPayload) -> Dict[str, Any]:
    """Mô phỏng máy trạng thái LangGraph của quy trình phân xử khiếu nại."""
    transitions = [
        {
            "step": 1,
            "node": "load_evidence",
            "status": "COMPLETED",
            "data": {
                "dispute_id": payload.dispute_id,
                "claimed_amount": payload.claimed_amount,
                "media_count": 2 if payload.has_checkin_snapshot and payload.has_checkout_snapshot else 0
            },
            "description": "Nạp gói bằng chứng phiên đỗ (log vào, log ra, ảnh chụp camera barrier)."
        },
        {
            "step": 2,
            "node": "analyze_evidence",
            "status": "COMPLETED",
            "data": {
                "plate_match": True,
                "gate_sensor_delay_minutes": 15.2,
                "barrier_event": "SENSOR_TIMEOUT_DETECTED"
            },
            "description": "Trích xuất đặc trưng thị giác và timestamp đối chiếu sự cố barie."
        },
        {
            "step": 3,
            "node": "retrieve_policy",
            "status": "COMPLETED",
            "data": {
                "applicable_rule": "Điều 5 - Quy chế xử lý khiếu nại (Quy_che_xu_ly_khieu_nai_dieu_5.pdf)",
                "rule_content": "Trường hợp barie kẹt > 10 phút, hệ thống tự động trừ thời gian trễ khỏi phí tính."
            },
            "description": "Truy xuất quy định hoàn phí tương ứng từ kho tri thức pgvector."
        },
        {
            "step": 4,
            "node": "validate_evidence",
            "status": "COMPLETED",
            "data": {
                "is_valid": payload.has_checkin_snapshot and payload.has_checkout_snapshot,
                "route": "draft" if (payload.has_checkin_snapshot and payload.has_checkout_snapshot) else "review"
            },
            "description": "Kiểm tra tính toàn vẹn của bằng chứng trước khi sinh đề xuất."
        },
        {
            "step": 5,
            "node": "draft_recommendation",
            "status": "COMPLETED",
            "data": {
                "proposed_verdict": "APPROVE_PARTIAL_REFUND",
                "recommended_amount": payload.claimed_amount,
                "justification": f"Xác nhận sự cố barie trễ {15.2} phút theo Điều 5. Đề xuất hoàn {payload.claimed_amount:,.0f} VNĐ."
            },
            "description": "Dự thảo phương án giải quyết dựa trên quy chế và bằng chứng."
        },
        {
            "step": 6,
            "node": "human_review",
            "status": "AWAITING_STAFF_SIGN_OFF",
            "data": {
                "requires_human_approval": True,
                "assigned_role": "PARKING_LOT_SUPERVISOR",
                "auto_refund_permitted": False
            },
            "description": "Chuyển giao cho Giám sát bãi xe ký duyệt (ngăn chặn AI tự ý chi trả tiền)."
        }
    ]

    return {
        "success": True,
        "dispute_id": payload.dispute_id,
        "workflow": "LangGraph StateGraph [Bounded Dispute Recommendation]",
        "nodes_traversed": len(transitions),
        "steps": transitions,
        "final_status": "AWAITING_STAFF_SIGN_OFF"
    }
