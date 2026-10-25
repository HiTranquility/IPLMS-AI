# 🏷️ ISSUE-009: Bổ Sung Test Hồi Quy UI Khi API Lỗi, Timeout Hoặc Phiên Hết Hạn

> **Đích:** `docs/projects/issues/10-2026/ISSUE-009-console-ui-error-resilience-tests/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🟢 Resolved (Chờ merge PR) |
| **Người phụ trách** | Dương (@23110012) |
| **Ngày tạo** | 2026-10-24 |
| **Phạm vi** | `ai/ui` (`ui/src/api/client.test.ts`, `ui/src/pages/Copilot/CopilotLabPage.test.tsx`) |
| **Liên quan** | IPLMS ISSUE-126, BOARD việc 5 của Dương |

## 🎯 Mục tiêu

Bổ sung bộ test hồi quy tự động cho giao diện AI Console (`ai/ui`) khi gặp các tình huống lỗi từ API, đứt kết nối/timeout, hoặc phiên hết hạn:
1. Kiểm thử tầng `apiClient` (`request`, `requestOne`) xử lý chuẩn xác lỗi mạng/timeout (`NETWORK`), lỗi máy chủ 500 không trả JSON hợp lệ (`HTTP_500`), lỗi 403 (`FORBIDDEN`), và dữ liệu rỗng (`EMPTY`).
2. Kiểm thử màn hình `CopilotLabPage` và `ReviewForm`:
   - Khi tải danh sách lượt hỏi bị lỗi 500 hoặc timeout: hiển thị `ErrorBlock` (`role="alert"`) kèm mã lỗi và nút **Thử lại** (`onRetry`), cho phép tải lại thành công khi máy chủ phục hồi.
   - Khi gửi kết quả chấm (`POST /review`) gặp lỗi 403 (`FORBIDDEN`), 401 (`NO_SESSION` - hết hạn phiên), hoặc 500 (`INTERNAL_ERROR`): hiển thị thông báo lỗi trung thực, **tuyệt đối không báo lưu thành công giả** (`"Đã lưu kết quả chấm."`).

## 📋 Tiêu chí chấp nhận

- [x] Phủ test tầng `apiClient` cho các ca: lỗi mạng/timeout (`NETWORK`), HTTP 500 body hỏng, HTTP 403 `FORBIDDEN`, và `requestOne` trả mảng rỗng (`EMPTY`).
- [x] Phủ test `CopilotLabPage` khi API `/copilot/turns` trả lỗi 500 và bấm **Thử lại** (`onRetry`) phục hồi thành công.
- [x] Phủ test `ReviewForm` khi API `/review` trả lỗi 403 `FORBIDDEN`, 401 `NO_SESSION`, hoặc 500: hiện `role="alert"` và không hiện thông báo lưu thành công giả.
- [x] Chạy `tsc --noEmit` và `vitest run` pass 100%.

## 🛠️ Kết quả thực hiện

- Đã bổ sung 4 test cases vào `ui/src/api/client.test.ts` (tổng 7/7 pass).
- Đã bổ sung 3 test cases vào `ui/src/pages/Copilot/CopilotLabPage.test.tsx` (tổng 6/6 pass).
- Đã kiểm tra `script/check_branch_policy.py`: PASS.
