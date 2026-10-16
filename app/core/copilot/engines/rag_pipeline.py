"""Grounded retrieval-augmented generation pipeline for Copilot."""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, Iterable
import time

from app.config import get_config
from app.core.copilot.guardrails.guardrail_manager import guardrail_manager
from app.core.copilot.prompts.prompt_manager import prompt_manager
from app.core.exceptions import EmbeddingError, RagPipelineError
from app.infra.database.pgvector_client import pgvector_client
from app.infra.embedding import embedding_client
from app.infra.llm.llm_factory import llm_factory
from app.infra.monitoring.ai_logger import ai_telemetry_logger
from app.util.logger import logger


SYSTEM_PROMPT = prompt_manager.get_prompt("copilot_rag_system")

NO_CONTEXT_ANSWER = (
    "Mình chưa tìm thấy thông tin đủ liên quan trong kho tri thức để trả lời "
    "chắc chắn. Bạn hãy chọn đúng bãi xe hoặc nhờ chủ bãi bổ sung quy chế."
)


def _sources(chunks: Iterable[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(str(chunk["source"]) for chunk in chunks if chunk.get("source")))


def _context(chunks: Iterable[dict[str, Any]]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        source = chunk.get("source") or "không rõ nguồn"
        parts.append(f"[{index}] [Nguồn: {source}]\n{chunk['content']}")
    return "\n\n".join(parts)


def _confidence(chunks: list[dict[str, Any]]) -> float:
    if not chunks:
        return 0.0
    # Retrieval confidence, not an invented LLM certainty score. A weighted
    # blend rewards a strong first hit without ignoring disagreement below it.
    scores = [max(0.0, min(1.0, float(chunk.get("similarity", 0.0)))) for chunk in chunks]
    value = scores[0] * 0.7 + (sum(scores) / len(scores)) * 0.3
    return round(value, 4)


class RagPipelineEngine:
    def __init__(self, embedder=None, vector_store=None, llm=None) -> None:
        self.embedder = embedder or embedding_client
        self.vector_store = vector_store or pgvector_client
        self.llm = llm or llm_factory
        config = get_config().llm
        self.top_k = config.rag_top_k
        self.min_similarity = config.rag_min_similarity

    def _retrieve_from_seed(self, query: str, parking_lot_id: str | None) -> list[dict[str, Any]]:
        import json
        import os
        import re

        candidates_paths = [
            os.path.join(os.getcwd(), "data", "knowledge", "regulations_seed.json"),
            os.path.join("/app", "data", "knowledge", "regulations_seed.json"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/knowledge/regulations_seed.json")),
        ]
        seed_path = next((p for p in candidates_paths if os.path.exists(p)), None)
        if not seed_path:
            return []

        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                seeds = json.load(f)
        except Exception:
            return []

        STOPWORDS = {
            "là", "có", "và", "của", "cho", "các", "tại", "trong", "được", "những",
            "một", "này", "thì", "khi", "sau", "theo", "gì", "bao", "nhiêu", "thế",
            "nào", "ở", "ra", "sao", "với", "đến", "từ", "hãy", "tôi", "mình",
            "bạn", "biết", "về", "cách", "làm", "như", "hay"
        }
        q_lower = query.lower()
        all_words = re.findall(r'\w+', q_lower)
        keywords = [w for w in all_words if len(w) >= 2 and w not in STOPWORDS]
        if not keywords:
            keywords = [w for w in all_words if len(w) >= 2]

        if not keywords:
            return []

        scored = []
        for item in seeds:
            lot = item.get("parking_lot_id")
            if parking_lot_id and lot and lot != parking_lot_id:
                continue
            if not parking_lot_id and lot:
                continue

            content = item.get("content", "")
            title = item.get("title", "")

            matched_kw_count = 0
            score = 0.0
            for kw in keywords:
                hit = False
                if kw in title.lower():
                    score += 2.0
                    hit = True
                if kw in content.lower():
                    score += 1.0
                    hit = True
                if hit:
                    matched_kw_count += 1

            if matched_kw_count == 0:
                continue

            match_ratio = matched_kw_count / len(keywords)
            similarity = round(match_ratio * 0.70 + min(1.0, score / (len(keywords) * 2.5)) * 0.30, 4)
            if similarity >= self.min_similarity:
                scored.append({
                    "content": content,
                    "source": item.get("source", "regulations_seed.json"),
                    "category": item.get("category", "general"),
                    "similarity": similarity,
                    "_score": score,
                })

        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored[:self.top_k]

    async def _retrieve(self, query_text: str, parking_lot_id: str | None) -> list[dict[str, Any]]:
        query = query_text.strip()
        if not query:
            raise ValueError("Câu hỏi không được để trống.")
        try:
            vector = await self.embedder.embed_query(query)
            return await self.vector_store.search_similar_chunks(
                vector,
                query_text=query,
                parking_lot_id=parking_lot_id,
                top_k=self.top_k,
                min_similarity=self.min_similarity,
            )
        except RagPipelineError as exc:
            if not isinstance(self.vector_store, pgvector_client.__class__):
                raise
            logger.warning("Không kết nối được pgvector (%s), fallback sang local knowledge seed.", exc)
            return self._retrieve_from_seed(query, parking_lot_id)
        except EmbeddingError as exc:
            logger.warning("Embedding không khả dụng (%s), fallback sang local knowledge seed.", exc)
            return self._retrieve_from_seed(query, parking_lot_id)
        except Exception as exc:
            if not isinstance(self.vector_store, pgvector_client.__class__):
                raise RagPipelineError("Không truy xuất được kho tri thức.") from exc
            logger.warning("Lỗi truy xuất kho tri thức (%s), fallback sang local seed.", exc)
            return self._retrieve_from_seed(query, parking_lot_id)

    async def query(self, query_text: str, parking_lot_id: str | None = None) -> Dict[str, Any]:
        if not query_text or not query_text.strip():
            raise ValueError("Câu hỏi không được để trống.")
        start_time = time.perf_counter()
        logger.info(
            "Executing RAG query query_chars=%d lot_scoped=%s",
            len(query_text),
            bool(parking_lot_id),
        )

        # 1. Rào chắn đầu vào (Rủi ro 1: Prompt Injection, Rủi ro 2: Out of scope thô)
        guard_in = guardrail_manager.check_input(query_text)
        if not guard_in.is_safe:
            lat = round((time.perf_counter() - start_time) * 1000.0, 2)
            ai_telemetry_logger.record(
                endpoint="/api/copilot/ask",
                model=getattr(self.llm, "model", "local"),
                prompt_version=prompt_manager.default_version,
                tools_called=[],
                input_tokens=len(query_text.split()),
                output_tokens=len((guard_in.refusal_message or "").split()),
                latency_ms=lat,
                status="REFUSED",
            )
            return {
                "answer": guard_in.refusal_message or NO_CONTEXT_ANSWER,
                "sources": [],
                "confidence": 0.0,
                "refused": True,
                "guardrail_triggered": guard_in.risk_type,
                "prompt_version": prompt_manager.default_version,
                "latency_ms": lat,
            }

        # 2. Truy xuất tài liệu ngữ cảnh
        chunks = await self._retrieve(query_text, parking_lot_id)
        sources = _sources(chunks)

        # 3. Rào chắn phạm vi & độ liên quan (Rủi ro 2: Out of scope - ADR-0008)
        guard_scope = guardrail_manager.check_scope_and_chunks(query_text, chunks, self.min_similarity)
        if not guard_scope.is_safe or not chunks:
            lat = round((time.perf_counter() - start_time) * 1000.0, 2)
            ai_telemetry_logger.record(
                endpoint="/api/copilot/ask",
                model=getattr(self.llm, "model", "local"),
                prompt_version=prompt_manager.default_version,
                tools_called=[],
                input_tokens=len(query_text.split()),
                output_tokens=len((guard_scope.refusal_message or "").split()),
                latency_ms=lat,
                status="REFUSED",
            )
            return {
                "answer": guard_scope.refusal_message or NO_CONTEXT_ANSWER,
                "sources": [],
                "confidence": 0.0,
                "refused": True,
                "guardrail_triggered": guard_scope.risk_type,
                "prompt_version": prompt_manager.default_version,
                "latency_ms": lat,
            }

        # 4. Nạp System Prompt có versioning (Mục 4.2)
        system_prompt = prompt_manager.get_prompt("copilot_rag_system")
        prompt_meta = prompt_manager.get_metadata("copilot_rag_system")
        prompt_ver = prompt_meta.get("version", "v2")

        # 5. Sinh câu trả lời & Rào chắn phục hồi lỗi (Rủi ro 3: Timeout/Empty output fallback)
        status = "SUCCESS"
        try:
            raw_answer = await self.llm.generate_response(
                system_prompt,
                query_text.strip(),
                _context(chunks),
            )
            answer, is_fallback = guardrail_manager.validate_or_fallback_output(raw_answer, chunks)
            if is_fallback:
                status = "FALLBACK"
        except Exception as exc:
            logger.warning("Lỗi LLM inference (%s), kích hoạt fallback tài liệu cứu sinh.", exc)
            answer, _ = guardrail_manager.validate_or_fallback_output("", chunks)
            status = "FALLBACK"

        # 6. Ghi vết Telemetry & Chi phí
        lat = round((time.perf_counter() - start_time) * 1000.0, 2)
        in_toks = len((system_prompt + " " + query_text + " " + _context(chunks)).split())
        out_toks = len(answer.split())
        ai_telemetry_logger.record(
            endpoint="/api/copilot/ask",
            model=getattr(self.llm, "model", "local"),
            prompt_version=prompt_ver,
            tools_called=[],
            input_tokens=in_toks,
            output_tokens=out_toks,
            latency_ms=lat,
            status=status,
        )

        return {
            "answer": answer,
            "sources": sources,
            "confidence": _confidence(chunks),
            "refused": False,
            "guardrail_triggered": "FAILED_RESPONSE" if status == "FALLBACK" else None,
            "prompt_version": prompt_ver,
            "latency_ms": lat,
        }

    async def stream_query(
        self, query_text: str, parking_lot_id: str | None = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(
            "Executing RAG stream query_chars=%d lot_scoped=%s",
            len(query_text),
            bool(parking_lot_id),
        )

        # 1. Rào chắn đầu vào
        guard_in = guardrail_manager.check_input(query_text)
        if not guard_in.is_safe:
            yield {"token": guard_in.refusal_message or NO_CONTEXT_ANSWER, "is_finished": False, "sources": []}
            yield {"token": "", "is_finished": True, "sources": []}
            return

        chunks = await self._retrieve(query_text, parking_lot_id)
        sources = _sources(chunks)

        # 2. Rào chắn phạm vi & độ tương đồng
        guard_scope = guardrail_manager.check_scope_and_chunks(query_text, chunks, self.min_similarity)
        if not guard_scope.is_safe or not chunks:
            yield {"token": guard_scope.refusal_message or NO_CONTEXT_ANSWER, "is_finished": False, "sources": []}
            yield {"token": "", "is_finished": True, "sources": []}
            return

        # 3. Nạp Prompt & Stream
        system_prompt = prompt_manager.get_prompt("copilot_rag_system")
        async for token in self.llm.stream_response(
            system_prompt,
            query_text.strip(),
            _context(chunks),
        ):
            yield {"token": token, "is_finished": False, "sources": []}

        yield {"token": "", "is_finished": True, "sources": sources}


rag_pipeline = RagPipelineEngine()
