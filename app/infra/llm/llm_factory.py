"""OpenAI Responses API adapter for grounded RAG answers."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from app.config import get_config
from app.core.exceptions import ModelConfigurationError, ModelNotLoadedError, RagPipelineError
from app.util.logger import logger

try:
    from openai import APIConnectionError, NotFoundError
except ImportError:
    class NotFoundError(Exception):  # type: ignore[no-redef]
        pass

    class APIConnectionError(Exception):  # type: ignore[no-redef]
        pass


class LlmFactory:
    """Small adapter around Responses API, injectable in unit tests."""

    def __init__(self, api_key: str | None = None, client: Any | None = None,
                 profile: dict[str, Any] | None = None):
        config = get_config().llm
        self.api_key = api_key or config.llm_api_key
        self.base_url = (config.llm_base_url or "").strip() if not profile or profile["provider"] == "ollama" else ""
        self.model = profile["model"] if profile else config.llm_model
        self.timeout_seconds = profile["timeout_seconds"] if profile else config.llm_timeout_seconds
        self.max_retries = config.llm_max_retries
        self.max_output_tokens = profile["max_output_tokens"] if profile else config.llm_max_output_tokens
        self.reasoning_effort = profile["reasoning_effort"] if profile else "none"
        self.profile_revision = f"{profile['task']}:{profile['revision']}" if profile else "env"
        self.profile_id = profile["id"] if profile else ""
        self._profile = profile is not None
        self._client = client

    async def for_task(self, task: str) -> "LlmFactory":
        """Read the active revision per request so replicas see activation promptly."""
        from app.infra.database.model_policy_store import model_policy_store

        if not model_policy_store.db_url:
            return self
        profile = await model_policy_store.get_active(task)
        return LlmFactory(profile=profile) if profile else self

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        # Endpoint riêng (Ollama…) không cần key thật; OpenAI thì bắt buộc.
        api_key = "ollama" if self.base_url else self.api_key
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
        request = {
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
        if self.reasoning_effort != "none" and self.uses_openai:
            request["reasoning"] = {"effort": self.reasoning_effort}
        return request

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
        except (RagPipelineError, ModelNotLoadedError, ModelConfigurationError):
            raise
        except NotFoundError as exc:
            logger.warning(f"Model '{self.model}' not found on provider: {exc}")
            raise ModelConfigurationError(f"Provider không có model '{self.model}'.") from exc
        except APIConnectionError as exc:
            logger.warning(f"Cannot connect to provider '{self.base_url or 'OpenAI'}': {exc}")
            target = self.base_url or "OpenAI"
            raise ModelConfigurationError(f"Không kết nối được provider '{target}'.") from exc
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
        target_model = model or self.model
        if not self.uses_openai:
            return await self._generate_json_via_chat(
                instructions, input_text, schema_name, schema, target_model
            )
        try:
            kwargs = dict(
                model=target_model,
                instructions=instructions,
                input=input_text,
                max_output_tokens=self.max_output_tokens if self._profile else max(self.max_output_tokens, 4000),
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
            if self.reasoning_effort != "none":
                kwargs["reasoning"] = {"effort": self.reasoning_effort}
            response = await self._get_client().responses.create(**kwargs)
            payload = json.loads((response.output_text or "").strip() or "null")
            if not isinstance(payload, dict):
                raise RagPipelineError("Mô hình không trả về JSON đúng định dạng.")
            return payload
        except (RagPipelineError, ModelNotLoadedError, ModelConfigurationError):
            raise
        except NotFoundError as exc:
            logger.warning(f"Model '{target_model}' not found on provider: {exc}")
            raise ModelConfigurationError(f"Provider không có model '{target_model}'.") from exc
        except APIConnectionError as exc:
            logger.warning(f"Cannot connect to provider '{self.base_url or 'OpenAI'}': {exc}")
            target = self.base_url or "OpenAI"
            raise ModelConfigurationError(f"Không kết nối được provider '{target}'.") from exc
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
        target_model = model or self.model
        try:
            completion = await self._get_client().chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": input_text},
                ],
                max_tokens=self.max_output_tokens if self._profile else max(self.max_output_tokens, 4000),
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "schema": schema, "strict": True},
                },
            )
            content = (completion.choices[0].message.content or "").strip()
            payload = json.loads(content or "null")
        except (RagPipelineError, ModelNotLoadedError, ModelConfigurationError):
            raise
        except NotFoundError as exc:
            logger.warning(f"Model '{target_model}' not found on provider: {exc}")
            raise ModelConfigurationError(f"Provider không có model '{target_model}'.") from exc
        except APIConnectionError as exc:
            logger.warning(f"Cannot connect to provider '{self.base_url or 'Ollama'}': {exc}")
            target = self.base_url or "Ollama"
            raise ModelConfigurationError(f"Không kết nối được provider '{target}'.") from exc
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
        except (RagPipelineError, ModelNotLoadedError, ModelConfigurationError):
            raise
        except NotFoundError as exc:
            logger.warning(f"Model '{self.model}' not found on provider: {exc}")
            raise ModelConfigurationError(f"Provider không có model '{self.model}'.") from exc
        except APIConnectionError as exc:
            logger.warning(f"Cannot connect to provider '{self.base_url or 'OpenAI'}': {exc}")
            target = self.base_url or "OpenAI"
            raise ModelConfigurationError(f"Không kết nối được provider '{target}'.") from exc
        except Exception as exc:
            logger.exception("Responses API stream failed")
            raise RagPipelineError("Luồng trả lời từ OpenAI bị gián đoạn.") from exc


llm_factory = LlmFactory()
