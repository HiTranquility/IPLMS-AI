"""Nghiệp vụ Trợ lý Hỏi Đáp RAG & Trọng Tài Tranh Chấp."""
from typing import AsyncGenerator

from app.core.copilot.dtos.copilot_dto import (
    AnswerChunk,
    AskQuestionRequest,
    CopilotAnswer,
    DisputeArbitrationRequest,
    DisputeVerdict,
)
from app.core.copilot.engines.rag_pipeline import rag_pipeline
from app.core.exceptions import FeatureNotImplementedError
from app.util.logger import logger


class CopilotService:
    @staticmethod
    async def ask_question(request: AskQuestionRequest) -> CopilotAnswer:
        """Answer through the real embedding → pgvector → Responses pipeline."""
        result = await rag_pipeline.query(
            request.query,
            parking_lot_id=request.parking_lot_id,
            preview=request.preview,
        )
        return CopilotAnswer(
            answer=result["answer"],
            sources=result["sources"],
            confidence=result["confidence"],
        )

    @staticmethod
    async def stream_answer(request: AskQuestionRequest) -> AsyncGenerator[AnswerChunk, None]:
        """Stream the same grounded pipeline without buffering the full answer."""
        async for chunk in rag_pipeline.stream_query(
            request.query,
            parking_lot_id=request.parking_lot_id,
            preview=request.preview,
        ):
            yield AnswerChunk(
                token=chunk["token"],
                is_finished=chunk["is_finished"],
                sources=chunk["sources"],
            )

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
