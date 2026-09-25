# core/knowledge — Nạp tài liệu quy chế vào kho tri thức (pgvector)

> Trạng thái (2026-09-25): chạy thật; cần `AI_LLM_API_KEY` cho bước embedding. Nạp = **bản nháp** — khách chỉ thấy sau khi scope qua bộ test và được xuất bản ([core/knowledge_eval](../knowledge_eval/README.md), ISSUE-009).

## Luồng nạp một file

```text
backend owner|admin/knowledge-documents (POST, multipart ≤8MB, .pdf/.docx/.txt/.md, kiểm quyền scope)
  └─ grpc KnowledgeService.IngestDocument → app/api/grpc/handlers/knowledge_handler.py
       └─ services/ingestion_service.ingest
            ├─ engines/document_parser.parse_document      (timeout 20s — chặn PDF độc)
            │     đối chiếu magic bytes (%PDF-, PK..) với đuôi file · PDF: pypdf · DOCX: python-docx
            │     rỗng → NoTextLayerError (PDF scan) · sai định dạng → UnsupportedFormatError · >8MB → DocumentTooLargeError
            ├─ engines/chunker.chunk_text
            │     cắt theo "Điều/Chương/Mục/Phần N" hoặc heading Markdown; dài quá mới cắt tiếp
            │     theo đoạn văn; ~1500 ký tự, chồng 200, bỏ đoạn <100
            ├─ infra/embedding/embedding_client.embed_texts  lô 64, retry 429/5xx
            └─ infra/database/pgvector_client.save_draft_version   MỘT transaction:
                  tài liệu đang có nháp → thay nháp tại chỗ; chưa có → phiên bản mới (max+1)
                  bản PUBLISHED không bị đụng; nạp lại sang bãi khác → chặn
backend lưu bản gốc: Storage knowledge/{bãi|global}/{documentId}/v{n}
```

Trạng thái trả về: `SUCCESS` · `NO_TEXT_LAYER` · `UNSUPPORTED_FORMAT` · `FILE_TOO_LARGE` · `EMBEDDING_FAILED`.

## Dữ liệu (ai-db, schema tự tạo/nâng cấp trong `pgvector_client.ensure_schema`)

`knowledge_documents` (1 dòng/tài liệu, `parking_lot_id` NULL = chung) → `knowledge_document_versions` (DRAFT → TESTED → PUBLISHED → ARCHIVED; tối đa 1 nháp + 1 PUBLISHED, ép bằng unique index) → `knowledge_chunks` (`version_id`, embedding `vector(1536)`, HNSW + GIN full-text).

## Khác

- `ListDocuments` (phiên bản mới nhất + bản khách đang thấy), `DeleteDocument(draft_only)`.
- CLI: `python -m app.script.ingest_knowledge <file> --parking-lot-id <bãi> [--publish]` — `--publish` bỏ qua bộ test, chỉ cho vận hành phía server. Seed demo: `python app/script/seed_regulations.py` (xuất bản luôn).
- File mẫu thử nạp: `data/knowledge/demo-upload/` (MD/TXT/DOCX/PDF + 2 file phải bị từ chối).
- Test: `test_document_parser.py`, `test_chunker.py`, `test_ingestion_service.py`, `test_embedding_client.py`.
