# 🐛 bug-017: Chat Studio gửi tham số mà API không nhận, nên mọi câu hỏi đều nhận 422

> **Đích:** `docs/projects/bugs/bug-017-chat-studio-luon-422/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed (chờ PR) — nhánh `bugfix/bug-017-2026-10-chat-studio-contract` |
| **Môi trường** | `develop@5f8e753` |

## Hành vi thực tế

Ở tab "Chat tương tác" của Copilot Lab, mỗi câu hỏi gửi `POST /tools/copilot/stream` với body `{query, parking_lot_id, min_similarity, top_k, temperature}`. Model `AskIn` khai `extra="forbid"` và chỉ có `query` với `parking_lot_id`, nên FastAPI trả 422 trước khi gọi tới service. UI ném `HTTP 422`. Các thanh trượt Temperature, Top-K và Min similarity trong Inspector cũng không thể có tác dụng, vì backend không đọc ba giá trị này.

## Hành vi mong đợi

Có hai cách, cần chốt một:

- (a) Backend nhận và áp dụng ba tham số, có giới hạn và kiểm quyền `ai:prompt:edit`.
- (b) UI không gửi ba tham số và ẩn phần điều chỉnh tham số.

Dù chọn cách nào cũng cần thêm test hợp đồng giữa body UI và `AskIn`.

## Tái hiện

```bash
# trong ai/, venv của repo
.venv/Scripts/python.exe -c "from app.api.rest.routes.console_tools_controller import AskIn; AskIn.model_validate({'query':'x','parking_lot_id':None,'min_similarity':0.35,'top_k':4,'temperature':0.2})"
# → ValidationError: extra_forbidden min_similarity, top_k, temperature
```

## Bằng chứng

- `ui/src/pages/Copilot/components/ChatStudio/ChatStudio.tsx:128-154`: body có 5 trường.
- `app/api/rest/routes/console_tools_controller.py:34-37`: `AskIn` có `extra="forbid"` và chỉ 2 trường.
- `ChatStudio.test.tsx` mock `fetch` nên không phát hiện được lệch hợp đồng này. Suite UI vẫn xanh (48/48).

## Sửa / kiểm chứng

Chủ dự án chốt OPEN-01 = (a): backend nhận tham số. Ngày 2026-10-24.

**Hợp đồng mới của `POST /tools/copilot` và `/tools/copilot/stream`:** `AskIn` thêm 3 trường tuỳ chọn, vẫn giữ `extra="forbid"`:

| Trường | Kiểu / biên | Mặc định (không gửi) |
|---|---|---|
| `min_similarity` | float 0–1 | `rag_min_similarity` của cấu hình |
| `top_k` | int 1–10 | `rag_top_k` của cấu hình |
| `temperature` | float 0–1 | 0.2 như trước |

- `app/api/rest/routes/console_tools_controller.py:37-51`: `ASK_BODY_FIELDS` và `AskIn`, truyền `payload.tuning()` xuống service.
- `app/core/console/services/tools_service.py`: `try_copilot` và `try_copilot_stream` nhận 3 tham số. Cả lượt thử vẫn đòi quyền `ai:prompt:edit`, gồm cả tham số thử.
- `app/core/copilot/dtos/copilot_dto.py:25`: `AskQuestionRequest` mang 3 trường; `tuning_kwargs()` chỉ chuyển giá trị đã đặt, nên caller cũ (gRPC, REST inference) không đổi.
- `app/core/copilot/engines/rag_pipeline.py:127`: `_limits()` dùng `top_k` theo yêu cầu, còn ngưỡng tương đồng hiệu lực là **max(cấu hình, yêu cầu)**. Tham số thử chỉ làm truy xuất chặt hơn, không hạ được cổng NO_CONTEXT, và output guard vẫn chạy như cũ (ADR-0029). Engine dùng chung giữa các request nên không sửa `self.*`.
- `app/infra/llm/llm_factory.py:195,363`: `temperature` đi tới Chat Completions. Ở Responses API chỉ gửi khi không bật reasoning, vì model reasoning của OpenAI không nhận tham số này.
- UI: `ui/src/pages/Copilot/components/ChatStudio/askContract.ts` (`ASK_BODY_FIELDS`, `buildAskBody`). `ChatStudio.tsx:156` gửi đúng body, gọi `API_BASE` thay vì đoán `apiBase` theo URL. Lỗi non-2xx nay ném `ApiError` với thông điệp thật (`:165`).
- Lỗi phát hiện thêm khi sửa: UI đọc `parsed.chunk`/`parsed.content`/`parsed.citations`, trong khi server gửi `token`/`sources`. Vì vậy dù hết 422 thì câu trả lời vẫn không hiện. Đã sửa ở `ChatStudio.tsx:196`. Bỏ luôn câu giả "Đã xử lý yêu cầu thành công." khi rỗng (`:241`) và bỏ tốc độ t/s ước lượng theo độ dài chuỗi.

**Kiểm chứng (2026-10-24, venv tạm + Postgres 16 cục bộ):**

- `python -m unittest test.test_console_tools test.test_console_copilot_lab`: 17 test OK. Test mới ở `test/test_console_tools.py:77` (`ChatStudioContractTest`: body 5 trường hợp lệ, ngoài biên và trường lạ bị chặn, tham số tới Copilot, HTTP `/tools/copilot/stream` trả 200 qua TestClient thay vì 422) và `:135` (`RagLimitsTest`).
- `test_rag_pipeline`, `test_llm_factory`, `test_output_guard`, `test_arbitrate_dispute`: OK. `test_copilot_usage` (1 error) và `test_model_policy`: lỗi thiếu stub gRPC, đã có từ trước khi sửa (đã chạy lại trên code cũ, kết quả như nhau).
- UI: `ChatStudio.test.tsx` thêm 2 ca. (1) Body gửi có khoá đúng bằng `ASK_BODY_FIELDS` và token SSE hiện ra. (2) 422 → hiện lỗi thật, không có câu trả lời giả.
- Chưa chạy: gọi LLM thật (Ollama/OpenAI) để xem `temperature` có tác dụng; chưa xem trên browser.
