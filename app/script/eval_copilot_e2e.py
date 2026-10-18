"""Eval Copilot end-to-end: embedding + pgvector + LLM thật qua ``rag_pipeline.query``.

Khác ``eval_retrieval`` (chỉ đo truy xuất): script này chấm đúng thứ khách nhận —
trả lời hay từ chối, có trích đúng nguồn không, và độ trễ p50/p95.

Case ``answer`` mà không nguồn kỳ vọng nào có trong kho đang nạp được tách nhóm
``not_in_corpus``: với kho đó, từ chối mới là đúng, còn "trả lời" nhiều khả năng
là bịa. Không gộp nhóm này vào tỉ lệ trả lời.

Chuẩn bị (IPLMS ISSUE-126 review-6/7):
  1. Postgres có pgvector, ``AI_DATABASE_URL`` trỏ vào đó.
  2. Nạp demo: ``python -m app.script.seed_regulations`` (script này ghi đè
     ``data/knowledge/regulations_seed.json`` — chạy xong thì khôi phục bằng git).
  3. Chạy: ``python -m app.script.eval_copilot_e2e --out report.json``
     (thêm ``--dataset data/knowledge/eval_set_heldout.json`` cho bộ giữ riêng).

Cột ``best_vector_similarity`` là similarity vector cao nhất trong kho cho câu
hỏi — dùng để hiệu chỉnh ``AI_RAG_MIN_SIMILARITY``. Hiệu chỉnh trên ``eval_set``,
kiểm trên ``eval_set_heldout``; đừng chọn ngưỡng nhìn từ bộ held-out.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import time
from pathlib import Path
from typing import Any

import psycopg2

from app.config import get_config
from app.core.copilot.engines.rag_pipeline import PROMPT_VERSION, rag_pipeline
from app.infra.database.pgvector_client import pgvector_client
from app.infra.embedding import embedding_client

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "eval_set.json"

# LLM tự từ chối (status SUCCESS nhưng nói không đủ thông tin). Heuristic — cột
# `refused_by` tách "gate"/"guard" với "llm" để người đọc kiểm lại tay.
_LLM_REFUSAL = re.compile(
    r"(chưa|không)\s+(tìm\s+thấy|có)\s+(đủ\s+)?thông\s+tin"
    r"|không\s+đủ\s+thông\s+tin"
    r"|kho\s+tri\s+thức\s+(chưa|không)"
    r"|(chưa|không)\s+(được\s+)?(cung\s+cấp|nêu|đề\s+cập|mô\s+tả|cho\s+biết)"
    r"|không\s+thể\s+(trả\s+lời|xác\s+định|kết\s+luận)",
    re.IGNORECASE,
)


def _published_sources() -> set[str]:
    connection = psycopg2.connect(get_config().llm.database_url, connect_timeout=5)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT kc.source FROM knowledge_chunks kc
                JOIN knowledge_document_versions v ON v.id = kc.version_id
                WHERE v.status = 'PUBLISHED'
                """
            )
            return {row[0] for row in cursor.fetchall() if row[0]}
    finally:
        connection.close()


async def _best_vector_similarity(question: str, parking_lot_id: str | None) -> float:
    vector = await embedding_client.embed_query(question)
    rows = await pgvector_client.search_similar_chunks(
        vector, query_text=question, parking_lot_id=parking_lot_id, top_k=20, min_similarity=-1.0
    )
    return max((row["similarity"] for row in rows), default=0.0)


def _behaviour(result: dict[str, Any]) -> tuple[str, str]:
    status = result.get("status")
    if status == "NO_CONTEXT":
        return "refuse", "gate"
    if status == "REFUSED":
        return "refuse", "guard"
    if _LLM_REFUSAL.search(result.get("answer") or ""):
        return "refuse", "llm"
    return "answer", ""


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]


async def evaluate(paths: list[Path]) -> dict[str, Any]:
    corpus = _published_sources()
    rows = []
    for path in paths:
        for case in json.loads(path.read_text(encoding="utf-8")):
            expected = set(case["expected_sources"])
            if case["expected_behavior"] == "refuse":
                group = "should_refuse"
            else:
                group = "in_corpus" if expected & corpus else "not_in_corpus"
            best = await _best_vector_similarity(case["question"], case.get("parking_lot_id"))
            started = time.perf_counter()
            result = await rag_pipeline.query(case["question"], case.get("parking_lot_id"))
            latency = time.perf_counter() - started
            behaviour, refused_by = _behaviour(result)
            rows.append({
                "id": case["id"],
                "dataset": path.name,
                "group": group,
                "expected_behavior": case["expected_behavior"],
                "behaviour": behaviour,
                "refused_by": refused_by,
                "status": result.get("status"),
                "best_vector_similarity": round(best, 4),
                "sources": result.get("sources", []),
                "source_hit": bool(expected & set(result.get("sources", []))),
                "latency_s": round(latency, 3),
                "answer": (result.get("answer") or "")[:400],
            })
            print(
                f"{case['id']:>6} {group:<13} {behaviour:<6} {refused_by or '-':<5} "
                f"sim={best:.3f} {latency:6.2f}s hit={int(rows[-1]['source_hit'])}"
            )
    summary = {
        path.name: _summary([row for row in rows if row["dataset"] == path.name]) for path in paths
    }
    return {"config": _config_snapshot(), "corpus_sources": sorted(corpus),
            "summary": summary, "cases": rows}


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def group(name):
        return [row for row in rows if row["group"] == name]

    refuse, inside, outside = group("should_refuse"), group("in_corpus"), group("not_in_corpus")
    latencies = [row["latency_s"] for row in rows]
    llm_latencies = [row["latency_s"] for row in rows if row["refused_by"] != "gate"]
    def refused(group_rows):
        # `hard`: hệ thống chặn (cổng/guard) — chắc chắn. `refused` cộng thêm câu LLM
        # tự nói không đủ thông tin — theo regex, có thể đếm nhầm câu trả lời nửa vời.
        return {"total": len(group_rows),
                "refused": sum(r["behaviour"] == "refuse" for r in group_rows),
                "refused_hard": sum(r["refused_by"] in ("gate", "guard") for r in group_rows)}

    return {
        "should_refuse": refused(refuse),
        "in_corpus": {
            "total": len(inside),
            "answered": sum(r["behaviour"] == "answer" for r in inside),
            "source_hit": sum(r["source_hit"] for r in inside),
        },
        # Kho đang nạp không có tài liệu kỳ vọng: từ chối là đúng với kho này.
        "not_in_corpus": refused(outside),
        "refused_by_gate": sum(r["refused_by"] == "gate" for r in rows),
        "latency_s": {"p50": _percentile(latencies, 0.5), "p95": _percentile(latencies, 0.95)},
        "latency_llm_s": {"p50": _percentile(llm_latencies, 0.5), "p95": _percentile(llm_latencies, 0.95)},
    }


def _config_snapshot() -> dict[str, Any]:
    config = get_config()
    return {
        "embedding_model": config.embedding.model,
        "embedding_dimensions": config.embedding.dimensions,
        "llm_model": config.llm.llm_model,
        "rag_min_similarity": rag_pipeline.min_similarity,
        "rag_top_k": rag_pipeline.top_k,
        "prompt_version": PROMPT_VERSION,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval Copilot end-to-end (LLM + pgvector thật)")
    parser.add_argument("--dataset", type=Path, action="append",
                        help="File case; lặp lại để chạy nhiều bộ. Mặc định eval_set.json")
    parser.add_argument("--out", type=Path, help="Ghi báo cáo JSON đầy đủ (từng case)")
    args = parser.parse_args()
    report = asyncio.run(evaluate(args.dataset or [DEFAULT_DATASET]))
    print(json.dumps({"config": report["config"], "summary": report["summary"]},
                     ensure_ascii=False, indent=2))
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
