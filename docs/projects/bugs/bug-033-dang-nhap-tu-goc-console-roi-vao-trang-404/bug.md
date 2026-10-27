# 🐛 bug-033: Đăng nhập từ `/console/` xong rơi vào trang "Không có trang này"

> **Đích:** `docs/projects/bugs/bug-033-dang-nhap-tu-goc-console-roi-vao-trang-404/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🔧 Đã sửa trên nhánh `bugfix/bug-033-2026-10-dang-nhap-tu-goc-console-404` (`895eefb`), chờ PR vào develop |
| **Người nhận** | @HiTranquility |
| **Hạn** | — |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | — |
| **Người báo** | Claude Code (browser pane, vòng agent của [ISSUE-020](../../issues/10-2026/ISSUE-020-ke-hoach-demo-audit-ai-console/review/review-1.md)) |
| **Môi trường** | local · console `http://127.0.0.1:8090/console/` (ui/dist build 2026-10-26 19:13) · ai `6c52707` |

## Hành vi thực tế

Mở `http://127.0.0.1:8090/console/` khi chưa đăng nhập → nhập email/mật khẩu → nhập TOTP đúng → URL thành `/console/console/` và trang hiện **"Không có trang này · Về tổng quan"**. Đây là đường vào mặc định của mọi người dùng (README, phiếu audit), nên ai đăng nhập lần đầu cũng gặp trang lỗi ngay sau khi xác thực thành công.

Đăng nhập từ một trang con (`/console/settings`, `/console/vision/review`) thì không bị lặp tiền tố.

Bối cảnh: từ [ISSUE-003](../../issues/10-2026/ISSUE-003-console-root-routing-copilot-studio/issue.md) console chạy ở gốc `/`, còn `/console/` là đường tương thích ngược (`app/console_main.py:111-114`). Vào thẳng `/` không gặp lỗi này; nhưng `ui/README.md` và phiếu audit vẫn hướng dẫn mở `/console/` (OPEN-02 ở [review-1](../../issues/10-2026/ISSUE-020-ke-hoach-demo-audit-ai-console/review/review-1.md)).

## Hành vi mong đợi

Xác thực xong vào trang đầu tiên hợp với vai (phiếu audit K1.3), URL không lặp `/console`.

## Tái hiện

1. Đăng xuất (hoặc cửa sổ ẩn danh), mở `http://127.0.0.1:8090/console/`.
2. Mở "Tài khoản quản trị khẩn cấp", nhập email + mật khẩu của một tài khoản `console_admin`.
3. Nhập mã TOTP đúng.
4. **Quan sát:** URL `/console/console/`, nội dung "Không có trang này".

## Nguyên nhân gốc

- [`ui/src/pages/Auth/LoginPage.tsx:46-49`](../../../../ui/src/pages/Auth/LoginPage.tsx): `saveReturnTo` lưu `window.location.pathname` — đường dẫn **đầy đủ** gồm cả basename (`/console/`). Phép loại trừ `window.location.pathname !== '/'` không bắt được vì pathname là `/console/`, không phải `/`.
- [`ui/src/routes/AuthenticatedRoutes.tsx:23-27`](../../../../ui/src/routes/AuthenticatedRoutes.tsx): `<Navigate to={returnTo}>` chạy bên trong `BrowserRouter basename="/console"` ([`ui/src/main.tsx:14-21`](../../../../ui/src/main.tsx)), nên router cộng basename lần nữa → `/console/console/`.

Hướng sửa (chưa làm): lưu đường dẫn **tương đối với router** (`useLocation().pathname`) thay vì `window.location.pathname`, và bỏ qua khi đó là `/`.

## Bằng chứng

- Network: `POST /console/api/auth/password → 200`, `POST /console/api/auth/totp → 200`, sau đó URL `/console/console/`; `get_page_text` của `<main>` = "Không có trang này / Về tổng quan".
- Phiếu audit vòng 1 ghi K1.3 ✅ — có thể người audit đăng nhập từ một trang con, nên không gặp.

## Sửa / kiểm chứng

Nhánh `bugfix/bug-033-2026-10-dang-nhap-tu-goc-console-404`, commit `895eefb` (từ develop `bdeba06`):

- `ui/src/pages/Auth/LoginPage.tsx`: `saveReturnTo` lấy `useLocation().pathname + search` (đường dẫn theo router, đã bỏ basename) thay vì `window.location…`.
- `ui/src/pages/Auth/LoginPage.test.tsx` (mới): từ `/console/` không lưu trang quay lại; từ `/console/settings?tab=sessions` lưu `/settings?tab=sessions`. Cả 2 ca đỏ trước khi sửa, xanh sau.
- `npx tsc --noEmit` 0 lỗi · `npx vitest run` 22 file / 99 test pass · `vite build` OK.
- Browser thật: bản build chạy `vite preview` cổng 5191, proxy API sang console 8090; admin đăng nhập từ `/console/` → `/console/members`, không còn "Không có trang này".
- Convention audit: `review/audit-1.md` trên nhánh sửa, Kết luận ✅; A-1 (P3, thêm test với `BrowserRouter basename`) Deferred.
- Chưa kiểm trên browser ca trang con (chỉ unit test). Nợ cũ ngoài phạm vi: tham số `return_to` trên query vẫn được lưu nguyên văn.
