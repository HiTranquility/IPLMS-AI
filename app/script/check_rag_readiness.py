"""Fail-fast readiness check for a real IPLMS RAG environment.

This command never prints secrets or document content. By default it checks
configuration, PostgreSQL/pgvector schema and corpus counts. ``--check-openai``
also performs one real embedding request, which may incur a small API charge.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from app.config import get_config
from app.infra.database.pgvector_client import pgvector_client
from app.infra.embedding import embedding_client


async def check(*, check_openai: bool, require_documents: bool) -> int:
    config = get_config()
    report: dict[str, object] = {
        "ready": False,
        "configuration": {
            "api_key_configured": bool(config.llm.llm_api_key.strip()),
            "llm_model": config.llm.llm_model,
            "embedding_model": config.embedding.model,
            "embedding_dimensions": config.embedding.dimensions,
        },
        "database": {"connected": False},
        "openai": {"checked": check_openai, "reachable": None},
        "errors": [],
    }
    errors = report["errors"]
    assert isinstance(errors, list)

    if not config.llm.llm_api_key.strip():
        errors.append("AI_LLM_API_KEY chưa được cấu hình.")

    try:
        stats = await pgvector_client.get_knowledge_stats()
        report["database"] = {"connected": True, **stats}
        if require_documents and stats["chunks"] == 0:
            errors.append("Kho tri thức chưa có chunk; hãy chạy seed hoặc ingest tài liệu.")
    except Exception as exc:  # CLI boundary: report a concise operator-facing error.
        errors.append(f"PostgreSQL/pgvector: {exc}")

    if check_openai and config.llm.llm_api_key.strip():
        try:
            vector = await embedding_client.embed_query("IPLMS RAG readiness check")
            report["openai"] = {
                "checked": True,
                "reachable": True,
                "embedding_dimensions": len(vector),
            }
        except Exception as exc:  # CLI boundary, intentionally excludes request data.
            report["openai"] = {"checked": True, "reachable": False}
            errors.append(f"OpenAI embedding: {exc}")

    report["ready"] = not errors
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra readiness cho IPLMS RAG")
    parser.add_argument(
        "--check-openai",
        action="store_true",
        help="Gọi một embedding request thật (có thể phát sinh chi phí nhỏ)",
    )
    parser.add_argument(
        "--require-documents",
        action="store_true",
        help="Fail nếu knowledge_chunks đang rỗng",
    )
    args = parser.parse_args()
    return asyncio.run(
        check(check_openai=args.check_openai, require_documents=args.require_documents)
    )


if __name__ == "__main__":
    raise SystemExit(main())
