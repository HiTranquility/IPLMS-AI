# 🐛 bug-038: `rag_pipeline.query()` ném NameError `history`, mã audit `engine.reload_llm` thiếu ở UI

> **Đích:** `docs/projects/bugs/bug-038-rag-query-nameerror-history-va-thieu-ma-audit-reload-llm/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** | 2026-10-27 |
| **Người báo** | Claude (gộp thử bug-034 với develop sau PR #91) |
| **Ngày báo** | 2026-10-27 |
| **Môi trường** | develop `e549127` |

## Hành vi thực tế

1. `app/core/copilot/engines/rag_pipeline.py:336`: commit `1d35cbf` (RAG đa lượt, vào develop qua PR #91) thêm `_enrich_retrieval_query(query_text, history)` vào `query()`, nhưng chỉ khai báo tham số `history` cho `stream_query()`. Mọi lượt hỏi không stream (`POST /api/copilot/ask`, `CopilotService.ask_question`, eval) đều ném `NameError: name 'history' is not defined`.
2. Cũng commit đó thêm `history=history` vào lời gọi `llm.stream_response(...)`, nhưng fake LLM trong `test/test_rag_pipeline.py` và `test/test_output_guard.py` chưa nhận tham số này, nên test stream báo `TypeError`.
3. Server ghi mã audit `engine.reload_llm` (`app/core/console/services/tools_service.py:799`), nhưng `ui/src/pages/Audit/auditActionCodes.json` và i18n `audit.actions` chưa có mã này. Trang `/audit` vì thế hiện mã thô, và `test_console_audit_codes` đỏ.

Tổng cộng trên develop: 12 test báo error và 1 test fail.

## Hành vi mong đợi

`query()` nhận `history` giống `stream_query()` (mặc định `None`, dùng để làm giàu câu truy vấn retrieval), và các lượt hỏi không stream trả lời bình thường. Trang Audit có nhãn VI/EN cho `engine.reload_llm`.

## Sửa / kiểm chứng

- `rag_pipeline.py`: thêm tham số `history: Optional[List[Dict[str, Any]]] = None` cho `query()`. `generate_response` của LLM không nhận lịch sử hội thoại, nên lịch sử chỉ dùng cho retrieval, giống ý định của #91.
- Fake `stream_response` trong hai file test nhận thêm `history=None`, khớp chữ ký thật ở `llm_factory.py:375-378`.
- `auditActionCodes.json` thêm `"engine.reload_llm": "ml"`; `vi.ts` thêm "Nạp lại engine LLM"; `en.ts` thêm "LLM engine reloaded".
- `python -m unittest discover -s test` với `AI_CONSOLE_DEMO_SEED_ENABLED=false` (như CI): 594 test, OK (36 skip). `compileall` sạch.
- UI: `tsc --noEmit` ✅; `vitest run` 22 file / 100 test ✅; `vite build` ✅.

## Ghi chú

`test_copilot_usage.PipelineStatusTest.test_no_context` và `test_rag_pipeline.RagPipelineTest.test_no_context_does_not_call_llm` chỉ fail trên máy có `.env.dev` bật `AI_CONSOLE_DEMO_SEED_ENABLED`. `RagPipelineEngine` lúc đó đọc cờ từ config toàn cục, lấy seed demo để lấp chỗ trống thay vì trả NO_CONTEXT. Trên CI, nơi không có `.env.dev`, hai test này pass. Muốn chạy được ở mọi môi trường thì nên truyền `demo_seed_enabled=False` vào hai test đó. Phần này ngoài phạm vi bug này.
