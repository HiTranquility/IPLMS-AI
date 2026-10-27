"""Grounded retrieval-augmented generation pipeline for Copilot."""
from __future__ import annotations

import re
import time
from typing import Any, AsyncGenerator, Dict, Iterable

from app.config import get_config
from app.core.copilot.engines import output_guard
from app.core.copilot.guardrails import guardrail_manager
from app.core.copilot.prompts import prompt_manager
from app.infra.monitoring.ai_logger import ai_telemetry_logger
from app.core.exceptions import EmbeddingError, ModelNotLoadedError, RagPipelineError
from app.infra.database.pgvector_client import pgvector_client
from app.infra.embedding import embedding_client
from app.infra.llm.llm_factory import LlmFactory, llm_factory
from app.util.logger import logger


# Prompt hệ thống nằm ở `data/prompts/copilot_rag_system_<version>.txt` (đề Final §4.2).
# Nhãn telemetry = tên file + hash nội dung: sửa file mà quên tăng version vẫn thấy hash đổi.
_PROMPT_META = prompt_manager.get_metadata("copilot_rag_system")
SYSTEM_PROMPT = prompt_manager.get_prompt("copilot_rag_system")
PROMPT_VERSION = f"{_PROMPT_META['name']}_{_PROMPT_META['version']}#{_PROMPT_META['hash'][:8]}"
TOOLS = ["knowledge_search"]

NO_CONTEXT_ANSWER = (
    "Mình chưa tìm thấy thông tin đủ liên quan trong kho tri thức để trả lời "
    "chắc chắn. Bạn hãy chọn đúng bãi xe hoặc nhờ chủ bãi bổ sung quy chế."
)


def _sources(chunks: Iterable[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(str(chunk["source"]) for chunk in chunks if chunk.get("source")))


def _citation_key(name: str) -> str:
    return name.strip().casefold()


def _cited_sources(answer: str, chunks: Iterable[dict[str, Any]]) -> list[str]:
    """Only report citations actually written in the answer and present in context.

    LLM không luôn chép đúng tên file: chấp nhận cả số đoạn trong ngữ cảnh
    (``[2]``, ``[Nguồn: 2]``) và tên bỏ đuôi (``[Nguồn: quy-che]``). Tên không
    khớp đoạn nào vẫn bị bỏ — không nhận nguồn chưa từng được truy xuất.
    """
    chunk_list = list(chunks)
    available: dict[str, str] = {}
    for chunk in chunk_list:
        source = str(chunk.get("source") or "")
        if source:
            available.setdefault(_citation_key(source), source)
            stem = source.rsplit(".", 1)[0] if "." in source else source
            available.setdefault(_citation_key(stem), source)

    def resolve(reference: str) -> str | None:
        reference = reference.strip()
        if reference.isdigit():
            index = int(reference) - 1
            if 0 <= index < len(chunk_list) and chunk_list[index].get("source"):
                return str(chunk_list[index]["source"])
            return None
        return available.get(_citation_key(reference))

    cited = re.findall(
        r"\[\s*(?:Nguồn\s*:\s*)?([^\]]+?)\s*\]", answer, flags=re.IGNORECASE
    )
    references = [part for group in cited for part in re.split(r"\s*[,;]\s*", group)]
    return list(dict.fromkeys(
        source for source in map(resolve, references) if source is not None
    ))


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


def _usage_kw(llm: Any, usage: dict, temperature: float | None = None) -> dict:
    """Chỉ LlmFactory thật nhận `usage`/`temperature`; LLM giả trong test/script giữ chữ ký cũ."""
    if not isinstance(llm, LlmFactory):
        return {}
    kw: dict = {"usage": usage}
    if temperature is not None:
        kw["temperature"] = temperature
    return kw


def _log_guard(rule: str) -> None:
    # Không log câu hỏi/câu trả lời (có thể chứa dữ liệu khách), chỉ tên luật.
    logger.warning("Copilot output guard blocked answer rule=%s", rule)


def _enrich_retrieval_query(query: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """Bổ sung ngữ cảnh từ lịch sử hội thoại gần nhất cho câu truy vấn vector (Multi-turn RAG).

    Khi câu hỏi chứa đại từ chỉ định hoặc quá ngắn (ví dụ: 'bãi xe này ở đâu', 'bãi xe của ai'),
    hệ thống trích xuất thực thể/từ khóa chủ đạo từ lượt trước (tiêu đề tài liệu, tên bãi xe,
    địa danh) để vector search tìm đúng đoạn quy chế, vượt qua rào chắn ADR-0008 (>= 0.35).
    """
    if not history or not query:
        return query

    import re

    ANAPHORIC_PATTERNS = [
        r"\b(này|đó|nó|đấy|kia)\b",
        r"\b(ở đâu|chỗ nào|địa chỉ|ở vị trí nào)\b",
        r"\b(của ai|ai là|thuộc ai)\b",
        r"\b(quy định|quy chế|biểu phí|vé xe)\b",
        r"\b(chi tiết hơn|cụ thể hơn|nói rõ hơn)\b",
    ]
    is_referential = any(re.search(p, query, re.IGNORECASE) for p in ANAPHORIC_PATTERNS)
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 2]
    is_short = len(words) <= 7

    if not (is_referential or is_short):
        return query

    context_entities: list[str] = []
    for item in reversed(history[-4:]):
        content = item.get("content", "")
        # 1. Tìm tên bãi xe cụ thể trong nội dung hoặc trích dẫn
        lot_matches = re.findall(r"(?:Bãi\s+xe(?:\s+số)?\s+\w+|Landmark\s*81|Trung\s+tâm\s+Đào\s+tạo|phố\s+Vọng)", content, re.IGNORECASE)
        for lm in lot_matches:
            cleaned = lm.strip()
            if cleaned and not any(cleaned.lower() == e.lower() for e in context_entities):
                context_entities.append(cleaned)

        if context_entities:
            break

        # 2. Tìm tên tài liệu nếu không có tên bãi
        source_matches = re.findall(r"\[(?:Nguồn|Source):\s*([^\]]+)\]", content, re.IGNORECASE)
        for sm in source_matches:
            clean_name = re.sub(r"\.(pdf|docx|txt|md)", "", sm, flags=re.IGNORECASE).strip()
            if clean_name:
                context_entities.append(clean_name)
                break
        if context_entities:
            break

    if not context_entities:
        return query

    missing_entities = [e for e in context_entities if e.lower() not in query.lower()]
    if not missing_entities:
        return query

    enrichment = " ".join(missing_entities[:3])
    return f"{enrichment} {query}".strip()


class RagPipelineEngine:
    def __init__(self, embedder=None, vector_store=None, llm=None, demo_seed_enabled: bool | None = None) -> None:
        self.embedder = embedder or embedding_client
        self.vector_store = vector_store or pgvector_client
        self.llm = llm or llm_factory
        config = get_config().llm
        self.top_k = config.rag_top_k
        self.min_similarity = config.rag_min_similarity
        self._demo_seed_enabled = demo_seed_enabled

    def _limits(self, top_k: int | None, min_similarity: float | None) -> tuple[int, float]:
        """Tham số thử của console (ai bug-017) chỉ được làm truy xuất CHẶT hơn cấu hình.

        Hạ `min_similarity` dưới mức cấu hình sẽ nới cổng NO_CONTEXT, tức để LLM trả
        lời trên ngữ cảnh yếu, trái ADR-0029; nên ngưỡng hiệu lực là max(cấu hình, yêu cầu).
        Không sửa `self.*` vì engine dùng chung giữa các request song song.
        """
        k = self.top_k if top_k is None else max(1, int(top_k))
        floor = self.min_similarity if min_similarity is None else max(self.min_similarity, float(min_similarity))
        return k, floor

    def _seed_fallback_enabled(self) -> bool:
        if self._demo_seed_enabled is not None:
            return self._demo_seed_enabled
        return get_config().console.demo_seed_enabled

    def _retrieve_from_seed(
        self, query: str, parking_lot_id: str | None,
        top_k: int | None = None, min_similarity: float | None = None,
    ) -> list[dict[str, Any]]:
        top_k, min_similarity = self._limits(top_k, min_similarity)
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
            if similarity >= min_similarity:
                scored.append({
                    "content": content,
                    "source": item.get("source", "regulations_seed.json"),
                    "category": item.get("category", "general"),
                    "similarity": similarity,
                    "_score": score,
                })

        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored[:top_k]

    async def _retrieve(
        self, query_text: str, parking_lot_id: str | None, preview: bool = False,
        top_k: int | None = None, min_similarity: float | None = None,
    ) -> list[dict[str, Any]]:
        k, floor = self._limits(top_k, min_similarity)
        query = query_text.strip()
        if not query:
            raise ValueError("Câu hỏi không được để trống.")
        try:
            vector = await self.embedder.embed_query(query)
            chunks = await self.vector_store.search_similar_chunks(
                vector,
                query_text=query,
                parking_lot_id=parking_lot_id,
                top_k=k,
                min_similarity=floor,
                preview=preview,
            )
            # Seed là quy chế demo dùng chung, chọn theo trùng chữ: ở production
            # không có chunk thì phải NO_CONTEXT (ai ADR-0002), chỉ dev/sandbox mới lấp.
            if not chunks and self._seed_fallback_enabled():
                seed_chunks = self._retrieve_from_seed(query, parking_lot_id, k, floor)
                if seed_chunks:
                    logger.info("pgvector không có chunk khớp, fallback sang %d seed chunks.", len(seed_chunks))
                    return seed_chunks
            return chunks
        except (RagPipelineError, ModelNotLoadedError, EmbeddingError) as exc:
            if not isinstance(self.vector_store, pgvector_client.__class__):
                raise
            logger.warning("Kho tri thức pgvector/embedding không khả dụng (%s), fallback sang local knowledge seed.", exc)
            return self._retrieve_from_seed(query, parking_lot_id, k, floor)
        except Exception as exc:
            if not isinstance(self.vector_store, pgvector_client.__class__):
                raise RagPipelineError("Không truy xuất được kho tri thức.") from exc
            logger.warning("Lỗi truy xuất kho tri thức (%s), fallback sang local seed.", exc)
            return self._retrieve_from_seed(query, parking_lot_id, k, floor)

    async def _grounded_chunks(
        self, query_text: str, parking_lot_id: str | None, preview: bool,
        top_k: int | None = None, min_similarity: float | None = None,
    ) -> list[dict[str, Any]]:
        """Rỗng khi không có đoạn nào khớp NGHĨA → NO_CONTEXT, không gọi LLM.

        Nhánh keyword của tìm kiếm lai không qua `min_similarity` (similarity 0),
        nên kho nhỏ gần như luôn trả về đoạn chỉ vì trùng chữ "xe"/"bãi". Không
        có đoạn vector nào đạt ngưỡng thì từ chối thay vì để LLM tự đoán
        (IPLMS ISSUE-126 review-6 S1).
        """
        chunks = await self._retrieve(query_text, parking_lot_id, preview, top_k, min_similarity)
        gate = guardrail_manager.check_scope_and_chunks(query_text, chunks, self._limits(top_k, min_similarity)[1])
        return chunks if gate.is_safe else []

    async def query(
        self, query_text: str, parking_lot_id: str | None = None, preview: bool = False,
        llm_override=None, top_k: int | None = None, min_similarity: float | None = None,
        temperature: float | None = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "Executing RAG query query_chars=%d lot_scoped=%s",
            len(query_text),
            bool(parking_lot_id),
        )
        retrieval_query = _enrich_retrieval_query(query_text, history)
        chunks = await self._grounded_chunks(retrieval_query, parking_lot_id, preview, top_k, min_similarity)
        if not chunks:
            return {"answer": NO_CONTEXT_ANSWER, "sources": [], "confidence": 0.0,
                    "status": "NO_CONTEXT", "usage": {}, "model": ""}

        llm = llm_override or (
            await self.llm.for_task("copilot_answer") if isinstance(self.llm, LlmFactory) else self.llm
        )
        context = _context(chunks)
        usage: dict = {}
        answer = await llm.generate_response(SYSTEM_PROMPT, query_text.strip(), context, **_usage_kw(llm, usage, temperature))
        meta = {"usage": usage, "model": str(getattr(llm, "model", "")),
                "model_revision": getattr(llm, "profile_revision", "")}
        rule = output_guard.violation(answer, context)
        if rule:
            _log_guard(rule)
            return {"answer": output_guard.GUARD_NOTICE, "sources": [],
                    "confidence": 0.0, "status": "REFUSED", **meta}
        return {
            "answer": answer,
            "sources": _cited_sources(answer, chunks),
            "confidence": _confidence(chunks),
            "status": "SUCCESS",
            **meta,
        }

    async def stream_query(
        self, query_text: str, parking_lot_id: str | None = None, preview: bool = False,
        top_k: int | None = None, min_similarity: float | None = None,
        temperature: float | None = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        start_time = time.perf_counter()
        logger.info(
            "Executing RAG stream query_chars=%d lot_scoped=%s",
            len(query_text),
            bool(parking_lot_id),
        )
        # 1. Rào chắn đầu vào (Mục 4.2: Prompt Injection)
        guard_in = guardrail_manager.check_input(query_text)
        if not guard_in.is_safe:
            refusal = guard_in.refusal_message or NO_CONTEXT_ANSWER
            lat = round((time.perf_counter() - start_time) * 1000.0, 2)
            ai_telemetry_logger.record(
                endpoint="/api/copilot/stream",
                model=getattr(self.llm, "model", "local"),
                prompt_version=PROMPT_VERSION,
                tools_called=[],
                input_tokens=len(query_text.split()),
                output_tokens=len(refusal.split()),
                latency_ms=lat,
                status="REFUSED",
            )
            yield {
                "token": refusal,
                "is_finished": False,
                "sources": [],
                "confidence": 0.0,
                "refused": True,
                "guardrail_triggered": guard_in.risk_type,
            }
            in_toks = len(query_text.split())
            out_toks = len(refusal.split())
            speed_tok_s = round(out_toks / (lat / 1000.0), 1) if lat > 0 else 0.0
            yield {
                "token": "",
                "is_finished": True,
                "sources": [],
                "confidence": 0.0,
                "refused": True,
                "guardrail_triggered": guard_in.risk_type,
                "prompt_version": PROMPT_VERSION,
                "latency_ms": lat,
                "status": "REFUSED",
                "usage": {"input_tokens": in_toks, "output_tokens": out_toks},
                "model": str(getattr(self.llm, "model", "")),
                "input_tokens": in_toks,
                "output_tokens": out_toks,
                "speed_tok_s": speed_tok_s,
                "context_tokens": in_toks,
                "context_limit": getattr(get_config().llm, "local_llm_ctx_size", 4096),
            }
            return

        retrieval_query = _enrich_retrieval_query(query_text, history)
        chunks = await self._grounded_chunks(retrieval_query, parking_lot_id, preview, top_k, min_similarity)
        if not chunks:
            lat = round((time.perf_counter() - start_time) * 1000.0, 2)
            yield {"token": NO_CONTEXT_ANSWER, "is_finished": False, "sources": []}
            yield {
                "token": "",
                "is_finished": True,
                "sources": [],
                "confidence": 0.0,
                "refused": False,
                "guardrail_triggered": None,
                "prompt_version": PROMPT_VERSION,
                "latency_ms": lat,
                "status": "NO_CONTEXT",
                "usage": {},
                "model": str(getattr(self.llm, "model", "")),
            }
            return

        sources = _sources(chunks)

        # 2. Rào chắn phạm vi & độ tương đồng (Mục 4.2: Scope Filter & ai ADR-0002)
        guard_scope = guardrail_manager.check_scope_and_chunks(
            retrieval_query, chunks, self._limits(top_k, min_similarity)[1]
        )
        if not guard_scope.is_safe:
            refusal = guard_scope.refusal_message or NO_CONTEXT_ANSWER
            lat = round((time.perf_counter() - start_time) * 1000.0, 2)
            ai_telemetry_logger.record(
                endpoint="/api/copilot/stream",
                model=getattr(self.llm, "model", "local"),
                prompt_version=PROMPT_VERSION,
                tools_called=[],
                input_tokens=len(query_text.split()),
                output_tokens=len(refusal.split()),
                latency_ms=lat,
                status="REFUSED",
            )
            yield {
                "token": refusal,
                "is_finished": False,
                "sources": [],
                "confidence": 0.0,
                "refused": True,
                "guardrail_triggered": guard_scope.risk_type,
            }
            in_toks = len(query_text.split())
            out_toks = len(refusal.split())
            speed_tok_s = round(out_toks / (lat / 1000.0), 1) if lat > 0 else 0.0
            yield {
                "token": "",
                "is_finished": True,
                "sources": [],
                "confidence": 0.0,
                "refused": True,
                "guardrail_triggered": guard_scope.risk_type,
                "prompt_version": PROMPT_VERSION,
                "latency_ms": lat,
                "status": "REFUSED",
                "usage": {"input_tokens": in_toks, "output_tokens": out_toks},
                "model": str(getattr(self.llm, "model", "")),
                "input_tokens": in_toks,
                "output_tokens": out_toks,
                "speed_tok_s": speed_tok_s,
                "context_tokens": in_toks,
                "context_limit": getattr(get_config().llm, "local_llm_ctx_size", 4096),
            }
            return

        # 3. Nạp Prompt & Stream
        llm = await self.llm.for_task("copilot_answer") if isinstance(self.llm, LlmFactory) else self.llm
        context = _context(chunks)
        tripped: list[str] = []
        answer_parts: list[str] = []
        usage: dict = {}
        async for token in output_guard.guard_stream(
            llm.stream_response(SYSTEM_PROMPT, query_text.strip(), context, history=history, **_usage_kw(llm, usage, temperature)),
            context,
            lambda rule: (tripped.append(rule), _log_guard(rule)),
        ):
            answer_parts.append(token)
            yield {"token": token, "is_finished": False, "sources": []}

        lat = round((time.perf_counter() - start_time) * 1000.0, 2)
        full_text = "".join(answer_parts)
        in_toks = len((SYSTEM_PROMPT + " " + query_text + " " + context).split())
        out_toks = len(full_text.split())
        speed_tok_s = round(out_toks / (lat / 1000.0), 1) if lat > 0 else 0.0
        status = "REFUSED" if tripped else "SUCCESS"
        usage["input_tokens"] = in_toks
        usage["output_tokens"] = out_toks

        ai_telemetry_logger.record(
            endpoint="/api/copilot/stream",
            model=str(getattr(llm, "model", "local")),
            prompt_version=PROMPT_VERSION,
            tools_called=[],
            input_tokens=in_toks,
            output_tokens=out_toks,
            latency_ms=lat,
            status=status,
        )

        final_sources = [] if tripped else (_cited_sources(full_text, chunks) or sources)
        citations: list[dict[str, Any]] = []
        if not tripped and chunks:
            cited_names = set(final_sources)
            seen_chunk_keys = set()
            for c in chunks:
                src = str(c.get("source", "") or c.get("title", ""))
                cid = str(c.get("chunk_id", "") or "")
                key = (src, cid or c.get("content", "")[:50])
                if (src in cited_names or not cited_names) and key not in seen_chunk_keys:
                    seen_chunk_keys.add(key)
                    citations.append({
                        "title": src,
                        "snippet": str(c.get("content", ""))[:800],
                        "score": round(float(c.get("similarity", 0.0)), 4),
                        "chunk_id": cid or None,
                        "document_id": str(c.get("document_id", "") or ""),
                    })

        yield {
            "token": "",
            "is_finished": True,
            "sources": final_sources,
            "citations": citations,
            "confidence": _confidence(chunks),
            "refused": bool(tripped),
            "guardrail_triggered": tripped[0] if tripped else None,
            "model_revision": getattr(llm, "profile_revision", ""),
            "prompt_version": PROMPT_VERSION,
            "latency_ms": lat,
            "status": status,
            "usage": usage,
            "model": str(getattr(llm, "model", "")),
            "answer": full_text,
            "input_tokens": in_toks,
            "output_tokens": out_toks,
            "speed_tok_s": speed_tok_s,
            "context_tokens": in_toks,
            "context_limit": getattr(get_config().llm, "local_llm_ctx_size", 4096),
        }


rag_pipeline = RagPipelineEngine()
