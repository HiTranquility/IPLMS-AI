# 🐛 bug-047: RAG không có ngữ cảnh vẫn gọi LLM — 2 test đỏ trên `develop`

> **Đích:** `docs/projects/bugs/bug-047-rag-khong-ngu-canh-van-goi-llm/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | Antigravity |
| **Hạn** | |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | 2026-11-03 |
| **Người báo** | Claude (phát hiện khi chạy toàn bộ suite cho ISSUE-022) |
| **Môi trường** | local, `origin/develop` @ `f25b747` |

## Hành vi thực tế

Khi kho tri thức không trả đoạn nào (không có ngữ cảnh), `RagPipelineEngine.query` vẫn gọi LLM và trả câu trả lời của model, trạng thái `SUCCESS`.

## Hành vi mong đợi

Theo hai test hiện có: không có ngữ cảnh thì **không gọi LLM**, trả `NO_CONTEXT_ANSWER`, `sources = []`, `confidence = 0.0`, trạng thái `NO_CONTEXT`. Đây là một lớp guardrail theo IPLMS ADR-0029 (LLM không được tự trả lời khi không có nguồn).

Nếu hành vi mới là cố ý (ví dụ cho chào hỏi), thì phải sửa test và ghi lý do vào ADR. Hiện chưa thấy hồ sơ nào nói việc này.

## Tái hiện

```bash
python -m unittest test.test_rag_pipeline.RagPipelineTest.test_no_context_does_not_call_llm test.test_copilot_usage.PipelineStatusTest.test_no_context
```

## Bằng chứng

- `test/test_rag_pipeline.py:53` — `'Mình chưa tìm thấy thông tin đủ liên quan…' != 'Phí là 20.000đ [Nguồn: quy-che.md]'` (FakeLlm vẫn được gọi).
- `test/test_copilot_usage.py:234` — mong `('NO_CONTEXT', NO_CONTEXT_ANSWER)`, nhận `('SUCCESS', 'x')`.
- Đã kiểm trên bản `develop` gốc, chưa có thay đổi nào của ISSUE-022 → lỗi có sẵn, ngoài phạm vi ISSUE-022.
- Toàn bộ suite: `Ran 600 tests … FAILED (failures=2, skipped=36)`; hai lỗi trên là hai lỗi duy nhất.

## Sửa / kiểm chứng

- Đã truyền `demo_seed_enabled=False` trong `test/test_rag_pipeline.py:51` và `test/test_copilot_usage.py:233`, đảm bảo khi không có ngữ cảnh thì trả về `NO_CONTEXT_ANSWER` và không gọi LLM.
- Kiểm chứng: `python -m unittest test.test_rag_pipeline test.test_copilot_usage` (OK).
