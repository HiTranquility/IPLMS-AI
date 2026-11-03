"""Quét lại tài liệu ĐÃ nạp bằng injection_scan (PROB-046 phase 2).

Bộ quét chỉ chạy lúc nạp, nên tài liệu nạp trước khi có nó chưa được gắn cờ —
kể cả bản đang PUBLISHED mà khách đang đọc. Script này tính lại cờ cho mọi đoạn
thuộc phiên bản chưa ARCHIVED. Đoạn còn khớp thì gắn cờ, đoạn hết khớp (luật quét
đã sửa) thì gỡ cờ cũ.

Mặc định CHỈ BÁO CÁO. ``--apply`` mới ghi ``knowledge_chunks.metadata``. Báo cáo
chỉ in tên tài liệu, phạm vi, trạng thái và một trích dẫn ≤ 80 ký tự — không in
toàn văn tài liệu.

Chạy:  python -m app.script.rescan_knowledge_injection [--apply]
"""
from __future__ import annotations

import argparse
import json

from psycopg2.extras import Json

from app.core.knowledge.guardrails.injection_scan import find_injection_phrases
from app.infra.database.pgvector_client import pgvector_client

_SELECT = """
    SELECT c.id::text, c.source, d.parking_lot_id, v.status, c.content, c.metadata
      FROM knowledge_chunks c
      JOIN knowledge_document_versions v ON v.id = c.version_id
      JOIN knowledge_documents d ON d.id = c.document_id
     WHERE v.status <> 'ARCHIVED'
     ORDER BY d.parking_lot_id NULLS FIRST, c.source, c.ordinal
"""


def plan(rows) -> tuple[list[tuple[str, dict]], dict]:
    """(các cập nhật cần ghi, báo cáo). Thuần, không I/O — test được."""
    updates: list[tuple[str, dict]] = []
    flagged: dict[tuple, dict] = {}
    for chunk_id, source, scope, status, content, metadata in rows:
        metadata = dict(metadata or {})
        flags = find_injection_phrases(content)
        if flags:
            entry = flagged.setdefault((scope or "", source, status), {
                "scope": scope or "(chung)", "source": source, "status": status,
                "chunks": 0, "sample": flags[0],
            })
            entry["chunks"] += 1
        if flags != metadata.get("injection_flags", []):
            if flags:
                metadata["injection_flags"] = flags
            else:
                metadata.pop("injection_flags", None)
            updates.append((chunk_id, metadata))
    report = {
        "scanned_chunks": len(rows),
        "flagged_documents": list(flagged.values()),
        "chunks_to_update": len(updates),
        "published_still_served": sum(1 for e in flagged.values() if e["status"] == "PUBLISHED"),
    }
    return updates, report


def _run(apply: bool) -> dict:
    connection = pgvector_client._connect_sync(register=False)
    try:
        with connection, connection.cursor() as cur:
            cur.execute(_SELECT)
            updates, report = plan(cur.fetchall())
            if apply:
                for chunk_id, metadata in updates:
                    cur.execute(
                        "UPDATE knowledge_chunks SET metadata = %s WHERE id = %s",
                        (Json(metadata), chunk_id),
                    )
            report["applied"] = apply
            return report
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="ghi cờ vào DB (mặc định chỉ báo cáo)")
    args = parser.parse_args()
    report = _run(args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Còn bản PUBLISHED bị gắn cờ = khách đang đọc nó: trả mã lỗi để CI/người chạy thấy.
    return 1 if report["published_still_served"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
