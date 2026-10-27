# 🐛 bug-037: Gateway Copilot nhận prompt dài tuỳ ý, output guard bị lách bằng cách tách chữ

> **Đích:** `docs/projects/bugs/bug-037-copilot-gateway-khong-gioi-han-prompt-va-guard-bi-lach-chu/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🔄 REVIEWING (đã sửa trên nhánh, chạm guard nên chờ techlead duyệt rồi mới merge) |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | |
| **Người báo** | Antigravity AI Security Fuzzing Agent |
| **Ngày báo** | 2026-10-26 |
| **Môi trường** | local / develop |
| **Đề xuất gốc** | [SUGGESTION-008](../../suggestions/10-2026/SUGGESTION-008-gioi-han-do-dai-prompt-gateway-va-chong-luan-chu-output-guard.md) |

## Hành vi thực tế

1. `POST /api/copilot/ask`, `POST /api/copilot/stream` và `GET /api/copilot/stream` không giới hạn độ dài `query`. Bộ fuzz gửi 100.000 ký tự vẫn nhận HTTP 200. Trong khi đó, endpoint nội bộ `/console/api/tools/copilot` đã giới hạn ở 2000 ký tự.
2. `output_guard._FREE` không bắt được câu "miễn phí" khi chữ bị tách bằng khoảng trắng hoặc dấu chấm (`m i ễ n   p h í`, `m.i.ễ.n p.h.í`), cũng không bắt được "không thu phí". Câu khẳng định sai về phí vì vậy lọt tới người dùng (ADR-0029).

## Hành vi mong đợi

- `query` phải có 1–2000 ký tự, `parking_lot_id` tối đa 128, `user_id` tối đa 64. Vượt giới hạn thì trả 422.
- Guard chặn được các biến thể tách chữ của "miễn phí" và câu "không thu phí" khi ngữ cảnh không có thông tin đó.

## Sửa / kiểm chứng

- `app/api/rest/routes/copilot_controller.py`: thêm `Field`/`Query` giới hạn độ dài cho `AskPayload` và `stream_copilot_get`.
- `app/core/copilot/engines/output_guard.py`: `_FREE` cho phép ký tự ngăn cách `[\s._-]` giữa các chữ, và thêm nhánh `không\s*thu\s*phí`.
- `test/test_output_guard.py`: thêm 3 ca lách chữ. `python -m unittest test.test_output_guard` ✅ (11 test).
