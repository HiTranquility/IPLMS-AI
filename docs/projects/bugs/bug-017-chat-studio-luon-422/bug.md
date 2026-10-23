# 🐛 bug-017: Chat Studio gửi tham số mà API không nhận, nên mọi câu hỏi đều nhận 422

> **Đích:** `docs/projects/bugs/bug-017-chat-studio-luon-422/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | 🆕 New / 🔴 hỏng luồng chính của [ISSUE-003](../../issues/10-2026/ISSUE-003-console-root-routing-copilot-studio/issue.md) |
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

Chưa sửa.
