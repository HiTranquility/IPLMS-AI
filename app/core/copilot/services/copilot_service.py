"""Nghiệp vụ Trợ lý Hỏi Đáp RAG & Trọng Tài Tranh Chấp."""
import time
from typing import AsyncGenerator
from uuid import uuid4

from app.core.copilot.dtos.copilot_dto import (
    AnswerChunk,
    AskQuestionRequest,
    CopilotAnswer,
    DisputeArbitrationRequest,
    DisputeVerdict,
)
from app.core.copilot.engines.rag_pipeline import PROMPT_VERSION, rag_pipeline
from app.core.copilot.services.usage_service import usage_service
from app.core.exceptions import FeatureNotImplementedError
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
                    confidence=chunk.get("confidence"),
                    refused=chunk.get("refused", False),
                    guardrail_triggered=chunk.get("guardrail_triggered"),
                    model_revision=chunk.get("model_revision", ""),
                    turn_id=turn_id if finished else "",
                    prompt_version=chunk.get("prompt_version", PROMPT_VERSION if finished else ""),
                    latency_ms=chunk.get("latency_ms"),
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


copilot_service = CopilotService()
