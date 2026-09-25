"""OpenAI Responses API adapter for grounded RAG answers."""
from __future__ import annotations

from typing import Any, AsyncGenerator

from app.config import get_config
from app.core.exceptions import RagPipelineError
from app.util.logger import logger


class LlmFactory:
    """Small adapter around Responses API, injectable in unit tests."""

    def __init__(self, api_key: str | None = None, client: Any | None = None):
        config = get_config().llm
        self.api_key = api_key or config.llm_api_key
        self.model = config.llm_model
        self.timeout_seconds = config.llm_timeout_seconds
        self.max_retries = config.llm_max_retries
        self.max_output_tokens = config.llm_max_output_tokens
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RagPipelineError(
                "Thiếu AI_LLM_API_KEY; Copilot chưa thể gọi mô hình ngôn ngữ."
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - lỗi đóng gói image
            raise RagPipelineError("Python package 'openai' chưa được cài.") from exc

        self._client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )
        return self._client

    def _request(self, system_prompt: str, user_query: str, context: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "instructions": system_prompt,
            "input": (
                "CÂU HỎI CỦA NGƯỜI DÙNG:\n"
                f"{user_query}\n\n"
                "NGỮ CẢNH ĐÃ TRUY XUẤT TỪ KHO TRI THỨC:\n"
                f"{context}"
            ),
            "max_output_tokens": self.max_output_tokens,
            # Nội dung quy chế/phiên gửi có thể nhạy cảm; không lưu response ở
            # phía provider trừ khi có quyết định governance riêng.
            "store": False,
        }

    async def generate_response(self, system_prompt: str, user_query: str, context: str) -> str:
        """Generate one grounded answer; never logs prompt or retrieved content."""
        try:
            response = await self._get_client().responses.create(
                **self._request(system_prompt, user_query, context)
            )
            answer = (response.output_text or "").strip()
            if not answer:
                raise RagPipelineError("Mô hình không trả về nội dung văn bản.")
            return answer
        except RagPipelineError:
            raise
        except Exception as exc:
            logger.exception("Responses API request failed")
            raise RagPipelineError("Không sinh được câu trả lời từ OpenAI.") from exc

    async def stream_response(
        self, system_prompt: str, user_query: str, context: str
    ) -> AsyncGenerator[str, None]:
        """Yield only semantic text deltas from a Responses API stream."""
        try:
            stream = await self._get_client().responses.create(
                **self._request(system_prompt, user_query, context),
                stream=True,
            )
            completed = False
            async for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", "")
                    if delta:
                        yield delta
                elif event_type == "response.completed":
                    completed = True
                elif event_type in {"error", "response.failed", "response.incomplete"}:
                    error = getattr(event, "error", None)
                    message = getattr(error, "message", None) or "Responses API stream failed."
                    raise RagPipelineError(str(message))
            if not completed:
                raise RagPipelineError("Luồng OpenAI kết thúc trước sự kiện response.completed.")
        except RagPipelineError:
            raise
        except Exception as exc:
            logger.exception("Responses API stream failed")
            raise RagPipelineError("Luồng trả lời từ OpenAI bị gián đoạn.") from exc


llm_factory = LlmFactory()
