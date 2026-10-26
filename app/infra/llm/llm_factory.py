"""OpenAI Responses API adapter for grounded RAG answers."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from app.config import get_config
from app.config.llm_config import DEFAULT_LOCAL_LLM_MODEL, NON_OLLAMA_MODEL_NAMES
from app.core.exceptions import ModelConfigurationError, ModelNotLoadedError, RagPipelineError
from app.util.logger import logger

try:
    from openai import APIConnectionError, NotFoundError
except ImportError:
    class NotFoundError(Exception):  # type: ignore[no-redef]
        pass

    class APIConnectionError(Exception):  # type: ignore[no-redef]
        pass


def _should_use_responses_api(client: Any, provider: str, has_api_key: bool) -> bool:
    if not hasattr(client, "responses"):
        return False
    if not hasattr(client, "chat"):
        return True
    return provider not in ("local", "ollama") and has_api_key


def _strip_thinking_tags(text: str) -> str:
    import re
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _copy_usage(source: Any, target: dict | None) -> None:
    """Chép số token nếu provider có báo; không báo thì để trống, không ước lượng."""
    if target is None or source is None:
        return
    for field in ("input_tokens", "output_tokens"):
        value = getattr(source, field, None)
        if isinstance(value, int):
            target[field] = value


class LlmFactory:
    """Small adapter around Responses API, injectable in unit tests."""

    def __init__(self, api_key: str | None = None, client: Any | None = None,
                 profile: dict[str, Any] | None = None):
        config = get_config().llm
        self.api_key = api_key or config.llm_api_key
        self.provider = (profile["provider"] if profile and "provider" in profile else getattr(config, "llm_provider", "local")).lower()
        raw_base = (config.llm_base_url or "").strip() if not profile or profile.get("provider") == "ollama" else ""
        import os
        if "host.docker.internal" in raw_base and not os.path.exists("/.dockerenv"):
            raw_base = raw_base.replace("host.docker.internal", "127.0.0.1")
        self.base_url = raw_base
        model_name = profile["model"] if profile else getattr(config, "active_model_name", config.llm_model)
        if self.provider in ("local", "ollama") and (not model_name or model_name in NON_OLLAMA_MODEL_NAMES):
            model_name = DEFAULT_LOCAL_LLM_MODEL
        self.model = model_name
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
        try:
            profile = await model_policy_store.get_active(task)
            return LlmFactory(profile=profile) if profile else self
        except Exception as exc:
            logger.warning("Không thể đọc active model policy profile (%s), dùng fallback mặc định.", exc)
            return self

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        config = get_config().llm
        provider = getattr(config, "llm_provider", "openai").lower()

        # Hỗ trợ Local LLM / Ollama linh hoạt
        active_prov = (self.provider or provider).lower()
        if active_prov in ("local", "ollama") and ("host.docker.internal" in self.base_url or not self.base_url):
            # A. Thử kết nối llama-server nếu đang chạy ở local_llm_url
            local_url = getattr(config, "local_llm_url", "http://127.0.0.1:8005/v1")
            llama_alive = False
            # Provider ollama không dò llama-server; URL health theo local_llm_url, không viết cứng.
            if active_prov == "local":
                try:
                    import urllib.request
                    health_url = f"{local_url.rstrip('/').removesuffix('/v1')}/health"
                    with urllib.request.urlopen(health_url, timeout=0.3) as r:
                        llama_alive = r.status == 200
                except Exception:  # noqa: BLE001 — server chưa bật thì chuyển sang Ollama
                    llama_alive = False

            if llama_alive:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    base_url=local_url,
                    api_key="local-llama",
                    timeout=self.timeout_seconds,
                    max_retries=1,
                )
                # llama-server chỉ nạp một file GGUF: báo đúng tên model đang chạy (A-40).
                self.model = getattr(config, "local_gguf_model_name", None) or self.model
                return self._client

            # B. Nếu llama-server không chạy, tự động kết nối Ollama local
            ollama_url = getattr(config, "ollama_url", "http://127.0.0.1:11434/v1")
            custom_base = getattr(config, "llm_base_url", "")
            target_base = custom_base or ollama_url
            import os
            if "host.docker.internal" in target_base and not os.path.exists("/.dockerenv"):
                target_base = target_base.replace("host.docker.internal", "127.0.0.1")
            if not target_base.endswith("/v1"):
                target_base = f"{target_base.rstrip('/')}/v1"

            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                base_url=target_base,
                api_key="ollama",
                timeout=self.timeout_seconds,
                max_retries=1,
            )
            # Rơi sang Ollama: tên GGUF của llama-server không dùng được ở đây.
            if not self.model or self.model in NON_OLLAMA_MODEL_NAMES:
                self.model = DEFAULT_LOCAL_LLM_MODEL
            return self._client

        api_key = "ollama" if (self.base_url or active_prov in ("local", "ollama")) else self.api_key
        if not api_key:
            logger.error("Thiếu AI_LLM_API_KEY; Copilot chưa thể gọi mô hình ngôn ngữ.")
            raise ModelNotLoadedError(
                "Trợ lý AI chưa được cấu hình khoá mô hình ngôn ngữ nên chưa trả lời được."
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RagPipelineError("Python package 'openai' chưa được cài.") from exc

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url or None,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )
        return self._client

    async def _aget_client(self) -> Any:
        """Bản dùng trong đường async: dò llama-server (urlopen đồng bộ) chạy ngoài event loop (A-41)."""
        if self._client is not None:
            return self._client
        return await asyncio.to_thread(self._get_client)

    @property
    def uses_openai(self) -> bool:
        """True khi gọi thẳng OpenAI; endpoint tương thích (Ollama…) thiếu vài tính năng."""
        return not self.base_url or "api.openai.com" in self.base_url

    def _request(
        self, system_prompt: str, user_query: str, context: str, temperature: float | None = None
    ) -> dict[str, Any]:
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
        elif temperature is not None:
            # Model reasoning của OpenAI không nhận temperature; chỉ gửi khi không bật reasoning.
            request["temperature"] = temperature
        return request

    async def generate_response(
        self, system_prompt: str, user_query: str, context: str, usage: dict | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate one grounded answer; never logs prompt or retrieved content.

        ``usage`` (tuỳ chọn) nhận số token provider báo về — dict riêng cho mỗi
        request, vì instance này có thể dùng chung giữa các request song song.
        """
        config = get_config().llm
        provider = getattr(config, "llm_provider", "local").lower()
        client = await self._aget_client()
        if _should_use_responses_api(client, provider, bool(self.api_key)):
            try:
                response = await client.responses.create(
                    **self._request(system_prompt, user_query, context, temperature)
                )
                _copy_usage(getattr(response, "usage", None), usage)
                answer = (response.output_text or "").strip()
                if not answer:
                    raise RagPipelineError("Mô hình không trả về nội dung văn bản.")
                return _strip_thinking_tags(answer)
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

        # Chat Completions (Local llama-server / Qwen3.5-4B-GGUF / Ollama)
        try:
            resp = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"CÂU HỎI CỦA NGƯỜI DÙNG:\n{user_query}\n\nNGỮ CẢNH ĐÃ TRUY XUẤT TỪ KHO TRI THỨC:\n{context}",
                    },
                ],
                max_tokens=self.max_output_tokens,
                temperature=0.2 if temperature is None else temperature,
            )
            raw_answer = (resp.choices[0].message.content or "").strip()
            answer = _strip_thinking_tags(raw_answer)
            if not answer:
                raise RagPipelineError("Mô hình Local LLM không trả về nội dung.")
            return answer
        except (RagPipelineError, ModelNotLoadedError, ModelConfigurationError):
            raise
        except Exception as exc:
            logger.exception("Local LLM request failed")
            raise RagPipelineError(f"Lỗi suy luận từ Local LLM: {exc}") from exc

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
            client = await self._aget_client()
            response = await client.responses.create(**kwargs)
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
            client = await self._aget_client()
            completion = await client.chat.completions.create(
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
        self, system_prompt: str, user_query: str, context: str, usage: dict | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Yield only semantic text deltas from a Responses API stream."""
        config = get_config().llm
        provider = getattr(config, "llm_provider", "local").lower()
        client = await self._aget_client()
        if _should_use_responses_api(client, provider, bool(self.api_key)):
            try:
                stream = await client.responses.create(
                    **self._request(system_prompt, user_query, context, temperature),
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
                        _copy_usage(getattr(getattr(event, "response", None), "usage", None), usage)
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
            return

        # Chat completions stream (Local llama-server / Qwen / Ollama)
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"CÂU HỎI CỦA NGƯỜI DÙNG:\n{user_query}\n\nNGỮ CẢNH ĐÃ TRUY XUẤT TỪ KHO TRI THỨC:\n{context}",
                    },
                ],
                max_tokens=self.max_output_tokens,
                temperature=0.2 if temperature is None else temperature,
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
        except (RagPipelineError, ModelNotLoadedError, ModelConfigurationError):
            raise
        except Exception as exc:
            logger.exception("Local LLM stream failed")
            raise RagPipelineError(f"Luồng suy luận từ Local LLM bị gián đoạn: {exc}") from exc


llm_factory = LlmFactory()
