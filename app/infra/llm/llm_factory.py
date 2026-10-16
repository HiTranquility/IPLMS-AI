"""OpenAI Responses API & Local llama-server adapter for grounded RAG answers."""
from __future__ import annotations

import re
from typing import Any, AsyncGenerator

from app.config import get_config
from app.core.exceptions import RagPipelineError
from app.infra.llm.llama_server_manager import llama_server_manager
from app.util.logger import logger


def _strip_thinking_tags(text: str) -> str:
    """Loại bỏ thẻ suy luận <think>...</think> nếu mô hình sinh ra."""
    if not text:
        return text
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    clean = re.sub(r'<think>.*$', '', clean, flags=re.DOTALL)
    return clean.strip()


class LlmFactory:
    """Adapter hỗ trợ cả OpenAI Responses API và Local llama.cpp (Qwen3.5-4B-GGUF)."""

    def __init__(self, api_key: str | None = None, client: Any | None = None):
        config = get_config().llm
        self.api_key = api_key or config.llm_api_key
        self.model = config.llm_model
        self.provider = getattr(config, "llm_provider", "local").lower()
        self.local_url = getattr(config, "local_llm_url", "http://127.0.0.1:8005/v1")
        self.timeout_seconds = config.llm_timeout_seconds
        self.max_retries = config.llm_max_retries
        self.max_output_tokens = config.llm_max_output_tokens
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        from openai import AsyncOpenAI

        # Nếu provider là local hoặc không có API key thì dùng local llama-server
        if self.provider == "local" or not self.api_key:
            try:
                llama_server_manager.ensure_server_running()
            except Exception as exc:
                logger.warning("Không thể tự động bật llama-server: %s", exc)

            self._client = AsyncOpenAI(
                base_url=self.local_url,
                api_key="local-llama",
                timeout=self.timeout_seconds,
                max_retries=1,
            )
            return self._client

        # Trường hợp dùng OpenAI Cloud
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )
        return self._client

    def _messages(self, system_prompt: str, user_query: str, context: str) -> list[dict[str, str]]:
        content = (
            "CÂU HỎI CỦA NGƯỜI DÙNG:\n"
            f"{user_query}\n\n"
            "NGỮ CẢNH ĐÃ TRUY XUẤT TỪ KHO TRI THỨC:\n"
            f"{context}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

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
            "store": False,
        }

    async def generate_response(self, system_prompt: str, user_query: str, context: str) -> str:
        """Generate one grounded answer; never logs prompt or retrieved content."""
        client = self._get_client()

        # 1. Hỗ trợ Responses API (được inject trong unit tests hoặc OpenAI mode)
        if hasattr(client, "responses") and not (
            hasattr(client, "chat") and (self.provider == "local" or not self.api_key)
        ):
            try:
                response = await client.responses.create(
                    **self._request(system_prompt, user_query, context)
                )
                answer = (response.output_text or "").strip()
                if not answer:
                    raise RagPipelineError("Mô hình không trả về nội dung văn bản.")
                return _strip_thinking_tags(answer)
            except RagPipelineError:
                raise
            except Exception as exc:
                logger.exception("Responses API request failed")
                raise RagPipelineError("Không sinh được câu trả lời từ OpenAI.") from exc

        # 2. Hỗ trợ Chat Completions API (Local llama-server / Qwen3.5-4B-GGUF)
        try:
            resp = await client.chat.completions.create(
                model="Qwen3.5-4B-Q4_K_M",
                messages=self._messages(system_prompt, user_query, context),
                max_tokens=self.max_output_tokens,
                temperature=0.2,
            )
            raw_answer = (resp.choices[0].message.content or "").strip()
            answer = _strip_thinking_tags(raw_answer)
            if not answer:
                raise RagPipelineError("Mô hình Local LLM không trả về nội dung.")
            return answer
        except RagPipelineError:
            raise
        except Exception as exc:
            logger.exception("Local LLM request failed")
            raise RagPipelineError(f"Lỗi suy luận từ Local LLM: {exc}") from exc

    async def stream_response(
        self, system_prompt: str, user_query: str, context: str
    ) -> AsyncGenerator[str, None]:
        """Yield semantic text deltas from stream."""
        client = self._get_client()

        # 1. Responses API Stream (Unit tests / OpenAI)
        if hasattr(client, "responses") and not (
            hasattr(client, "chat") and (self.provider == "local" or not self.api_key)
        ):
            try:
                stream = await client.responses.create(
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
            return

        # 2. Chat Completions API Stream (Local llama-server / Qwen3.5-4B-GGUF)
        try:
            stream = await client.chat.completions.create(
                model="Qwen3.5-4B-Q4_K_M",
                messages=self._messages(system_prompt, user_query, context),
                max_tokens=self.max_output_tokens,
                temperature=0.2,
                stream=True,
            )
            in_think = False
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content or ""
                if not delta:
                    continue
                if "<think>" in delta:
                    in_think = True
                    delta = delta.split("<think>")[0]
                if "</think>" in delta:
                    in_think = False
                    delta = delta.split("</think>")[-1]
                if not in_think and delta:
                    yield delta
        except RagPipelineError:
            raise
        except Exception as exc:
            logger.exception("Local LLM stream failed")
            raise RagPipelineError(f"Luồng suy luận từ Local LLM bị gián đoạn: {exc}") from exc


llm_factory = LlmFactory()
