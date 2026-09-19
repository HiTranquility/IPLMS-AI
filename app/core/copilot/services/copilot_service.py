"""Nghiệp vụ Trợ lý Hỏi Đáp RAG & Trọng Tài Tranh Chấp."""
from typing import AsyncGenerator

from app.core.copilot.dtos.copilot_dto import (
    AnswerChunk,
    AskQuestionRequest,
    CopilotAnswer,
    DisputeArbitrationRequest,
    DisputeVerdict,
)
from app.core.exceptions import FeatureNotImplementedError
from app.utils.logger import logger


class CopilotService:
    @staticmethod
    async def ask_question(request: AskQuestionRequest) -> CopilotAnswer:
        """[NEVER] bật lại cho tới khi chuỗi RAG phía sau là thật.

        Cùng lý do với ``arbitrate_dispute`` bên dưới. Ba tầng phía sau đều giả:

        - ``rag_pipeline.query`` dựng ``dummy_embedding = [0.0] * 1536`` — vector
          toàn số 0 nên mọi đoạn văn bản cách đều nhau, phép tìm kiếm ngữ nghĩa
          không tồn tại;
        - ``pgvector_client.search_similar_chunks`` trả một danh sách viết cứng,
          trích nguồn ``Quy_che_bai_xe_2026.pdf`` — file không hề có;
        - ``llm_factory.generate_response`` trả chuỗi cứng, và ``confidence`` bị
          gán ``0.95`` bất kể câu hỏi là gì.

        Một câu trả lời về BIỂU PHÍ trông tự tin 95% kèm trích dẫn quy chế là thứ
        người dùng sẽ tin và trả tiền theo. Nguy hiểm hơn hẳn một lỗi thẳng thắn.

        Việc thật cần làm trước khi mở lại: embedding thật + pgvector thật + LLM
        thật, nạp quy chế qua đường của IDEA-008 / ISSUE-004.
        """
        logger.warning(
            f"CopilotService.AskQuestion bị gọi bởi user {request.user_id} "
            f"— chuỗi RAG chưa triển khai, từ chối thay vì trả câu trả lời bịa."
        )
        raise FeatureNotImplementedError(
            "Trợ lý hỏi đáp chưa khả dụng: phần tra cứu quy chế (embedding + "
            "vector store + LLM) chưa được triển khai."
        )

    @staticmethod
    async def stream_answer(request: AskQuestionRequest) -> AsyncGenerator[AnswerChunk, None]:
        """Cùng lý do với ``ask_question`` — chỉ khác ở chỗ trả theo từng chunk.

        [GOTCHA] Đây là hàm generator: ``raise`` chỉ nổ khi người gọi bắt đầu
        lặp, không nổ lúc gọi hàm. Handler gRPC ``stream`` vẫn quy nó về
        UNIMPLEMENTED đúng như đường unary.
        """
        logger.warning(
            f"CopilotService.StreamAnswer bị gọi bởi user {request.user_id} "
            f"— chuỗi RAG chưa triển khai, từ chối thay vì phát chuỗi bịa."
        )
        raise FeatureNotImplementedError(
            "Trợ lý hỏi đáp chưa khả dụng: phần tra cứu quy chế (embedding + "
            "vector store + LLM) chưa được triển khai."
        )
        yield  # pragma: no cover — giữ hàm là generator cho đúng chữ ký

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
        phiên, đối chiếu với quy chế đã nạp qua RAG (xem IDEA-008), rồi mới kết
        luận. Toàn bộ chuỗi RAG hiện vẫn là giả — xem IDEA-008 §1.2.
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
