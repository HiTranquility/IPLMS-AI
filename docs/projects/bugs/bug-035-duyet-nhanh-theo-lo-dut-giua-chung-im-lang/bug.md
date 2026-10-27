# 🐛 bug-035: "Duyệt nhanh N mẫu khớp 100%" đứt giữa lô thì im lặng và để dòng cũ trên màn hình

> **Đích:** `docs/projects/bugs/bug-035-duyet-nhanh-theo-lo-dut-giua-chung-im-lang/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | 2026-10-27 |
| **Người báo** | Claude (rà trang Duyệt nhãn sau vòng demo ISSUE-020) |
| **Ngày báo** | 2026-10-27 |
| **Môi trường** | local / dev stack `iplms-ai-dev-console-1` |

## Hành vi thực tế

`ui/src/pages/Vision/ReviewPage.tsx` (`handleApproveAllExact`) gọi `decideLabel` lần lượt cho từng mẫu khớp 100% trong `try … finally` không có `catch`, và chỉ làm mới hàng đợi **sau khi cả vòng lặp chạy xong**. Nếu một request lỗi giữa lô (ví dụ reviewer khác vừa duyệt nhãn đó, server trả "Nhãn này đã được duyệt rồi."):

1. Lỗi thành unhandled promise rejection, màn hình không báo gì.
2. Hàng đợi không được làm mới: các nhãn đã duyệt ở đầu lô vẫn hiện, bấm Duyệt lại thì bị lỗi.
3. Kể cả khi lô chạy hết, trang chỉ làm mới `reviews` và `accuracy`. Số đếm `status` ở Tổng quan và `/audit` vẫn hiện dữ liệu cũ, khác với `useVisionMutation`, vốn làm mới cả nhóm `vision` lẫn `audit`.

## Hành vi mong đợi

Lô bị đứt thì trang hiện lỗi của server, và luôn làm mới hàng đợi, số đếm cùng nhật ký kiểm toán, để các nhãn đã duyệt biến khỏi danh sách.

## Tái hiện

Test `ui/src/pages/Vision/ReviewRowNames.test.tsx` › "Duyệt nhanh theo lô đứt giữa chừng": request decision thứ hai trả 409. Trên code cũ test đỏ (không có chữ lỗi, hàng đợi không được gọi lại).

## Sửa / kiểm chứng

- `ReviewPage.tsx`: thêm `catch` lưu lỗi rồi hiện bằng `ErrorBlock`; trong `finally` làm mới `queryKeys.vision.all()` và `queryKeys.audit.list()`.
- Test mới: đỏ trên code cũ, xanh trên code mới. `npx tsc --noEmit` ✅; `npx vitest run` 20 file, 95 test ✅.

## Ghi chú cùng vòng rà

Trong vòng demo, triệu chứng "bấm Duyệt mà số dòng không giảm" **không phải lỗi app**. Script `test/e2e_vision_pipeline_test.py` dùng `button:has-text('Duyệt')` rồi lấy `.first`. Bộ lọc `has-text` không phân biệt hoa thường, nên nó trúng nút chuyển không gian "Xưởng Gán nhãn & Kiểm duyệt", chỉ mở menu chứ không duyệt gì. Dù vậy, script vẫn ghi `reviewer_approve_success = True`. Thử bấm trực tiếp nút Duyệt của dòng trên stack dev thì 5 dòng còn 4. Script đã được sửa để lấy nút theo `aria-label` của dòng và chỉ đạt khi số dòng giảm đúng 1. TOTP secret và mật khẩu demo giờ đọc từ `E2E_TOTP_SECRET` / `E2E_DEMO_PASSWORD`, không còn ghi trong file.
