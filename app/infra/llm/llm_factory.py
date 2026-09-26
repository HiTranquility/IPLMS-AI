"""OpenAI Responses API adapter for grounded RAG answers."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from app.config import get_config
from app.core.exceptions import ModelNotLoadedError, RagPipelineError
from app.util.logger import logger


class LlmFactory:
    """Small adapter around Responses API, injectable in unit tests."""

    def __init__(self, api_key: str | None = None, client: Any | None = None):
        config = get_config().llm
        self.api_key = api_key or config.llm_api_key
        self.base_url = (config.llm_base_url or "").strip()
        self.model = config.llm_model
        self.timeout_seconds = config.llm_timeout_seconds
        self.max_retries = config.llm_max_retries
        self.max_output_tokens = config.llm_max_output_tokens
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        # Endpoint riêng (Ollama…) không cần key thật; OpenAI thì bắt buộc.
        api_key = self.api_key or ("ollama" if self.base_url else "")
        if not api_key:
            logger.error("Thiếu AI_LLM_API_KEY; Copilot chưa thể gọi mô hình ngôn ngữ.")
            raise ModelNotLoadedError(
                "Trợ lý AI chưa được cấu hình khoá mô hình ngôn ngữ nên chưa trả lời được."
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - lỗi đóng gói image
            raise RagPipelineError("Python package 'openai' chưa được cài.") from exc

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url or None,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )
        return self._client

    @property
    def uses_openai(self) -> bool:
        """True khi gọi thẳng OpenAI; endpoint tương thích (Ollama…) thiếu vài tính năng."""
        return not self.base_url or "api.openai.com" in self.base_url

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
        except (RagPipelineError, ModelNotLoadedError):
            raise
        except Exception as exc:
            logger.exception("Responses API request failed")
            raise RagPipelineError("Không sinh được câu trả lời từ OpenAI.") from exc

    async def generate_json(
        self,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        """Một lời gọi trả JSON đúng schema (Structured Outputs) — dùng cho bộ test.

        Không log prompt/nội dung; `store=False` như đường trả lời khách.
        """
        if not self.uses_openai:
            return await self._generate_json_via_chat(
                instructions, input_text, schema_name, schema, model
            )
        try:
            response = await self._get_client().responses.create(
                model=model or self.model,
                instructions=instructions,
                input=input_text,
                max_output_tokens=max(self.max_output_tokens, 4000),
                store=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "schema": schema,
                        "strict": True,
                    }
                },
            )
            payload = json.loads((response.output_text or "").strip() or "null")
            if not isinstance(payload, dict):
                raise RagPipelineError("Mô hình không trả về JSON đúng định dạng.")
            return payload
        except (RagPipelineError, ModelNotLoadedError):
            raise
        except Exception as exc:
            logger.exception("Responses API JSON request failed")
            raise RagPipelineError("Không nhận được kết quả JSON từ OpenAI.") from exc

    async def _generate_json_via_chat(
        self,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
        model: str | None,
    ) -> dict[str, Any]:
        """Structured Outputs qua Chat Completions (`response_format`).

        Ollama có `/v1/responses` nhưng tài liệu không liệt kê `text.format` —
        tham số bị bỏ qua thì model trả văn bản tự do. `response_format` của Chat
        Completions thì được hỗ trợ. JSON sai vẫn là lỗi, không nuốt.
        """
        try:
            completion = await self._get_client().chat.completions.create(
                model=model or self.model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": input_text},
                ],
                max_tokens=max(self.max_output_tokens, 4000),
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "schema": schema, "strict": True},
                },
            )
            content = (completion.choices[0].message.content or "").strip()
            payload = json.loads(content or "null")
        except (RagPipelineError, ModelNotLoadedError):
            raise
        except Exception as exc:
            logger.exception("Chat Completions JSON request failed")
            raise RagPipelineError("Không nhận được kết quả JSON từ mô hình ngôn ngữ.") from exc
        if not isinstance(payload, dict):
            raise RagPipelineError("Mô hình không trả về JSON đúng định dạng.")
        return payload

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
        except (RagPipelineError, ModelNotLoadedError):
            raise
        except Exception as exc:
            logger.exception("Responses API stream failed")
            raise RagPipelineError("Luồng trả lời từ OpenAI bị gián đoạn.") from exc


llm_factory = LlmFactory()
