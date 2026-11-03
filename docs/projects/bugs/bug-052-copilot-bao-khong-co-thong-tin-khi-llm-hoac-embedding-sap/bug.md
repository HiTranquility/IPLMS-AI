# 🐛 bug-052: Copilot báo "chưa tìm thấy thông tin" khi LLM/embedding sập, không báo lỗi AI

> **Đích:** `docs/projects/bugs/bug-052-copilot-bao-khong-co-thong-tin-khi-llm-hoac-embedding-sap/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | Antigravity |
| **Hạn** |  |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** | 2026-11-03 |
| **Người báo** | Claude Code, lượt test luồng AI trước nộp báo cáo (2026-10-31) |
| **Môi trường** | local Docker (`docker-compose.develop.yml`), `develop` `e07413a` |

## Hành vi thực tế

Tắt Ollama (cả LLM lẫn embedding đều chạy trên đó) rồi hỏi `POST /api/copilot/ask {"query":"Bai mo cua may gio?"}`. Kết quả trả về sau 68 ms:

```json
{"answer":"Mình chưa tìm thấy thông tin đủ liên quan trong kho tri thức…","refused":false,"guardrail_triggered":null,"mode":"rag_local"}
```

Service không sập: `/health` vẫn OK, ANPR vẫn HTTP 200. Như vậy phần "fallback cho tính năng không dùng AI" của đề §4.2 đã đạt. Nhưng người dùng bị báo nhầm là *kho tri thức không có thông tin*, trong khi lỗi thật là *AI đang không chạy*. Response cũng không có trường nào để frontend hay dashboard đếm "failed request".

Nguyên nhân: `rag_pipeline.py` bắt `EmbeddingError`/`RagPipelineError` khi truy xuất rồi lặng lẽ chuyển sang `_retrieve_from_seed` (khoảng dòng 314–323). Seed không khớp thì rơi vào nhánh `NO_CONTEXT_ANSWER`.

## Hành vi mong đợi

Đề §4.2 (rủi ro 3, "wrong or failed AI response"): khi AI lỗi phải có thông báo rõ, ví dụ "Trợ lý AI tạm thời không khả dụng, các chức năng khác vẫn dùng bình thường". Response phải có cờ phân biệt được, chẳng hạn `guardrail_triggered="FAILED_RESPONSE"` hoặc `status="AI_UNAVAILABLE"`, và telemetry đếm lượt này là failed.

## Tái hiện

1. Stack AI chạy ở chế độ develop, Ollama đang chạy: câu hỏi thường trả lời có nguồn.
2. Tắt Ollama (`taskkill /F /IM ollama.exe`).
3. Gọi lại `/api/copilot/ask`: nhận câu "chưa tìm thấy thông tin", `refused=false`, không có cờ lỗi.

## Bằng chứng

Lượt test 2026-10-31: HTTP 200, 0,075 s; `/health` = ok; `/api/anpr/recognize` = 200 khi LLM tắt.

## Sửa / kiểm chứng

- Bỏ hành vi tự động nuốt lỗi kết nối trong `app/infra/embedding/embedding_client.py` và `app/core/copilot/engines/rag_pipeline.py` (`_retrieve`), ném `EmbeddingError` khi dịch vụ embedding ngừng hoạt động thay vì rơi xuống seed rồi báo nhầm `NO_CONTEXT`.
- Cập nhật `app/api/rest/routes/copilot_controller.py` và `app/api/rest/routes/console_tools_controller.py` trả `refused=True`, `guardrail_triggered="FAILED_RESPONSE"`, `mode="ai_unavailable"` khi AI/Embedding lỗi, đồng thời loại bỏ `api_key_override` khỏi `AskPayload`.
- Bổ sung unit test trong `test/test_rag_pipeline.py`.
