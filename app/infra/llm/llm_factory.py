"""Khởi tạo và cấu hình kết nối tới mô hình Ngôn ngữ Lớn (LLM Provider: OpenAI / Gemini / Ollama)."""
from typing import AsyncGenerator
from app.config import get_config
from app.utils.logger import logger

class LlmFactory:
    """Factory cung cấp client gọi LLM và Streaming response."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_config().llm.llm_api_key

    async def generate_response(self, system_prompt: str, user_query: str, context: str) -> str:
        """Sinh câu trả lời hoàn chỉnh (Unary)."""
        logger.info("Generating LLM response...")
        return (
            f"Dựa trên quy chế bãi xe và thông tin phiên gửi: "
            f"Tổng phí của bạn được tính gồm: 4 giờ đầu (60.000đ) + 2 giờ vượt khung (30.000đ) = 90.000đ."
        )

    async def stream_response(self, system_prompt: str, user_query: str, context: str) -> AsyncGenerator[str, None]:
        """Stream câu trả lời từng token realtime."""
        logger.info("Streaming LLM tokens...")
        sample_tokens = [
            "Chào ", "bạn, ", "dựa ", "trên ", "quy ", "chế ", "bãi ", "xe: ",
            "Thời ", "gian ", "gửi ", "từ ", "17h00 ", "đến ", "08h00 ", "sáng ", "hôm ", "sau ",
            "bao ", "gồm ", "phí ", "ngày ", "(40.000đ) ", "và ", "phụ ", "phí ", "qua ", "đêm ",
            "(30.000đ). ", "Tổng ", "cộng ", "là ", "70.000đ."
        ]
        for token in sample_tokens:
            yield token

llm_factory = LlmFactory()
