"""Ingest a real regulation document into pgvector from the command line.

Example (run from ``ai/``):
  python -m app.script.ingest_knowledge ./data/rules.pdf --parking-lot-id <uuid>
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.enums import IngestStatus
from app.core.knowledge.dtos.knowledge_dto import IngestDocumentCommand
from app.core.knowledge.services import ingestion_service


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Nạp tài liệu thật vào IPLMS RAG")
    parser.add_argument("file", type=Path)
    parser.add_argument("--parking-lot-id", default=None)
    parser.add_argument("--category", default="regulation")
    parser.add_argument("--uploaded-by", default="cli")
    parser.add_argument(
        "--document-id",
        default=None,
        help="UUID ổn định để retry không tạo tài liệu/chunk trùng",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help=(
            "Xuất bản NGAY bản vừa nạp (bỏ qua bộ test). Chỉ dành cho vận hành phía "
            "server; owner/admin xuất bản qua giao diện, có cổng kiểm thử (ISSUE-009)."
        ),
    )
    args = parser.parse_args()

    path: Path = args.file.resolve()
    result = await ingestion_service.ingest(
        IngestDocumentCommand(
            file_data=path.read_bytes(),
            file_name=path.name,
            parking_lot_id=args.parking_lot_id,
            category=args.category,
            uploaded_by=args.uploaded_by,
            document_id=args.document_id,
        )
    )
    print(
        f"status={result.status.value} document_id={result.document_id} "
        f"chunks={result.chunk_count} elapsed_ms={result.process_time * 1000:.1f}"
    )
    if result.message:
        print(result.message)
    if result.status is not IngestStatus.SUCCESS:
        return 1
    if args.publish:
        from app.infra.database.pgvector_client import pgvector_client

        await pgvector_client.publish_versions(
            args.parking_lot_id, [result.version_id], args.uploaded_by
        )
        print(f"published version_no={result.version_no}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
