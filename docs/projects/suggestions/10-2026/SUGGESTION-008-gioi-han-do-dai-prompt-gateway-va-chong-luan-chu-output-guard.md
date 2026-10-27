# 🌱 SUGGESTION-008: Giới hạn độ dài prompt Gateway và chống lách chữ trong Output Guard

> **Đích:** `docs/projects/suggestions/10-2026/SUGGESTION-008-gioi-han-do-dai-prompt-gateway-va-chong-luan-chu-output-guard.md` · **Luật chung:** [templates/README](../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🔄 REVIEWING |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | |
| **Ngày** | 2026-10-26 |
| **Người đề xuất** | Antigravity AI Security Fuzzing Agent |
| **Techlead duyệt** | @HiTranquility — ⏳ chờ |
| **Làm trước khi duyệt?** | Có — đã thử nghiệm và hoàn tất kiểm chứng trên local |
| **Phạm vi** | `ai` (`app/api/rest/routes/copilot_controller.py`, `app/core/copilot/engines/output_guard.py`) |

## Đề xuất

1. **Giới hạn độ dài `query` cho public Gateway Copilot API:**
   - Trong `app/api/rest/routes/copilot_controller.py`, cập nhật `AskPayload`:
     ```python
     class AskPayload(BaseModel):
         query: str = Field(..., min_length=1, max_length=2000)
         parking_lot_id: Optional[str] = Field(None, max_length=128)
         user_id: Optional[str] = Field("test-user", max_length=64)
     ```
   - Thêm tham số kiểm soát tương tự cho GET/POST SSE endpoint `stream_copilot_get` / `stream_copilot_post`.
2. **Chuẩn hóa chuỗi trước khi kiểm tra vi phạm trong `output_guard.py`:**
   - Tương tự hàm `_fold()` đã được hiện thực rất tốt trong [injection_scan.py](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/core/knowledge/engines/injection_scan.py), `output_guard.violation` nên chuẩn hóa gộp các khoảng trắng giữa các chữ cái rời rạc (character-spacing bypass: `"m i ễ n   p h í"` -> `"miễn phí"`) hoặc gộp dấu chấm/gạch nối trước khi regex `_FREE` và `_URL` kiểm tra. Điều này ngăn chặn kẻ tấn công lợi dụng việc chèn khoảng trắng để lách bộ lọc của hệ thống.

## Vấn đề nó giải quyết

1. **Chống DoS và làm cạn kiệt tài nguyên / budget token:**
   - Hiện tại endpoint nội bộ AI Console (`/console/api/tools/copilot`) đã có schema `AskIn(query=Field(max_length=2000))`, nhưng endpoint public bên ngoài (`/api/copilot/ask` và `/api/copilot/stream`) lại chấp nhận payload dài bất kỳ (fuzz test đã gửi thành công 10,000 và 100,000 ký tự mà không bị chặn ở tầng validation).
   - Điều này tạo nguy cơ DoS bộ nhớ GPU/RAM khi model embedding sinh vector, hoặc gây tràn token context của LLM.
2. **Chống lách rào chắn thông tin sai lệch (Free Parking Misinformation):**
   - Bộ tấn công fuzzing phát hiện: khi LLM phát ra chuỗi có dấu cách giữa các ký tự `"Bãi mở cửa m i ễ n   p h í hôm nay"`, regex `_FREE` hiện tại bỏ sót và cho phép câu trả lời lọt tới người dùng.

## Phạm vi

- **Trong phạm vi:**
  - File `app/api/rest/routes/copilot_controller.py`
  - File `app/core/copilot/engines/output_guard.py`
  - Unit test kiểm chứng trong `test/test_copilot_streaming_api.py` và `test/test_output_guard.py`
- **Ngoài phạm vi:**
  - Thay đổi kiến trúc mô hình LLM hoặc pgvector schema.

## Bằng chứng / tham khảo

1. Kết quả kiểm thử Fuzzing battery `test_token_fuzzing_and_bugs.py`:
   - `[Gateway /api/copilot/ask] Length=100000 chars -> Status: 200`
   - `[FAIL/BUG] [Output Guard Evasion] Free claim with extra space: Violation returned: None`
2. Tham chiếu code hiện tại:
   - [copilot_controller.py#L35-L40](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/api/rest/routes/copilot_controller.py#L35-L40)
   - [output_guard.py#L21-L49](file:///C:/Users/Admin/Downloads/IPLMS/ai/app/core/copilot/engines/output_guard.py#L21-L49)

## Bước tiếp theo

1. Chờ Techlead @HiTranquility xem xét và phản hồi.
2. Bản sửa đã nằm trên nhánh `bugfix/bug-037-2026-10-copilot-prompt-limit-and-guard-obfuscation`, hồ sơ [bug-037](../../bugs/bug-037-copilot-gateway-khong-gioi-han-prompt-va-guard-bi-lach-chu/bug.md). Policy tên nhánh không nhận mã `SUGGESTION`, nên nhánh đặt theo mã bug. Chỉ merge khi đề xuất này 🟢 ACCEPTED và PR được techlead approve.
