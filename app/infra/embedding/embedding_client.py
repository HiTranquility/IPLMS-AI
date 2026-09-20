"""OpenAI embedding client used by both ingestion and RAG queries.

The SDK client is created lazily so pure unit tests and non-Copilot workers do
not require an API key at import time. Retries are deliberately limited to
transient HTTP failures; bad input and authentication errors fail immediately.
"""
from __future__ import annotations

import asyncio
from typing import Any, Iterable, List, Sequence

from app.config import get_config
from app.core.exceptions import EmbeddingError
from app.utils.logger import logger


def _status_code(exc: Exception) -> int | None:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _is_transient(exc: Exception) -> bool:
    status = _status_code(exc)
    return status == 429 or (status is not None and status >= 500) or isinstance(
        exc, (TimeoutError, ConnectionError)
    )


class EmbeddingClient:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client
        self._config = get_config().embedding
        self._api_key = get_config().llm.llm_api_key

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise EmbeddingError(
                "Thiếu AI_LLM_API_KEY; không thể sinh embedding cho kho tri thức."
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - lỗi đóng gói image
            raise EmbeddingError("Python package 'openai' chưa được cài.") from exc

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            timeout=self._config.timeout_seconds,
            # Retry được điều khiển tại đây để hành vi ingestion có thể kiểm thử.
            max_retries=0,
        )
        return self._client

    async def embed_query(self, text: str) -> List[float]:
        vectors = await self.embed_texts([text])
        return vectors[0]

    async def embed_texts(self, texts: Sequence[str] | Iterable[str]) -> List[List[float]]:
        values = list(texts)
        if not values:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in values):
            raise EmbeddingError("Không thể sinh embedding cho đoạn văn bản rỗng.")

        result: List[List[float]] = []
        batch_size = max(1, self._config.batch_size)
        for start in range(0, len(values), batch_size):
            batch = values[start : start + batch_size]
            result.extend(await self._embed_batch(batch))
        return result

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        attempts = max(0, self._config.max_retries) + 1

        for attempt in range(attempts):
            try:
                response = await client.embeddings.create(
                    model=self._config.model,
                    input=texts,
                    dimensions=self._config.dimensions,
                    encoding_format="float",
                )
                ordered = sorted(response.data, key=lambda item: item.index)
                vectors = [list(item.embedding) for item in ordered]
                if len(vectors) != len(texts):
                    raise EmbeddingError(
                        "OpenAI trả về số vector không khớp số đoạn đầu vào."
                    )
                if any(len(vector) != self._config.dimensions for vector in vectors):
                    raise EmbeddingError(
                        "Số chiều embedding không khớp schema knowledge_chunks."
                    )
                return vectors
            except EmbeddingError:
                raise
            except Exception as exc:
                if attempt + 1 >= attempts or not _is_transient(exc):
                    logger.exception("Embedding request failed")
                    raise EmbeddingError("Không sinh được embedding từ OpenAI.") from exc
                delay = min(8.0, 0.5 * (2**attempt))
                logger.warning(
                    "Embedding request tạm lỗi; thử lại lần %d/%d sau %.1fs",
                    attempt + 2,
                    attempts,
                    delay,
                )
                await asyncio.sleep(delay)

        raise EmbeddingError("Không sinh được embedding từ OpenAI.")  # pragma: no cover


embedding_client = EmbeddingClient()

