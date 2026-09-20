"""Evaluate retrieval independently from answer generation.

Prerequisite: ingest demo documents with ``python -m app.script.seed_regulations``
or replace the eval set with labels for the production document corpus.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.config import get_config
from app.infra.database.pgvector_client import pgvector_client
from app.infra.embedding import embedding_client


async def evaluate(path: Path, recall3_threshold: float) -> int:
    cases = json.loads(path.read_text(encoding="utf-8"))
    answerable = [case for case in cases if case["expected_sources"]]
    no_answer = [case for case in cases if not case["expected_sources"]]
    hits = {1: 0, 3: 0, 5: 0}
    reciprocal_rank = 0.0
    correct_abstentions = 0

    for case in cases:
        vector = await embedding_client.embed_query(case["question"])
        rows = await pgvector_client.search_similar_chunks(
            vector,
            case["question"],
            parking_lot_id=case.get("parking_lot_id"),
            top_k=5,
            min_similarity=get_config().llm.rag_min_similarity,
        )
        sources = [row["source"] for row in rows]
        expected = set(case["expected_sources"])
        if not expected:
            correct_abstentions += int(not sources)
            print(f"NO-ANSWER {'PASS' if not sources else 'FAIL'} | {case['question']}")
            continue

        rank = next((index for index, source in enumerate(sources, start=1) if source in expected), None)
        if rank:
            reciprocal_rank += 1.0 / rank
            for k in hits:
                hits[k] += int(rank <= k)
        print(
            f"rank={rank or '-':>2} expected={','.join(sorted(expected))} "
            f"got={','.join(sources) or '-'} | {case['question']}"
        )

    denominator = max(1, len(answerable))
    recall = {k: hits[k] / denominator for k in hits}
    mrr = reciprocal_rank / denominator
    abstention_precision = correct_abstentions / max(1, len(no_answer))
    print(
        "\n"
        f"recall@1={recall[1]:.3f} recall@3={recall[3]:.3f} "
        f"recall@5={recall[5]:.3f} MRR={mrr:.3f} "
        f"no-answer-precision={abstention_precision:.3f}"
    )
    return 0 if recall[3] >= recall3_threshold else 1


def main() -> int:
    default_path = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "eval_set.json"
    parser = argparse.ArgumentParser(description="Đo retrieval RAG IPLMS")
    parser.add_argument("--dataset", type=Path, default=default_path)
    parser.add_argument("--min-recall-at-3", type=float, default=0.8)
    args = parser.parse_args()
    return asyncio.run(evaluate(args.dataset, args.min_recall_at_3))


if __name__ == "__main__":
    raise SystemExit(main())
