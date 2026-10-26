# 🐛 bug-033: Đăng nhập từ `/console/` xong rơi vào trang "Không có trang này"

> **Đích:** `docs/projects/bugs/bug-033-dang-nhap-tu-goc-console-roi-vao-trang-404/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New |
| **Người nhận** | @HiTranquility |
| **Hạn** | — |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | — |
| **Người báo** | Claude Code (browser pane, vòng agent của [ISSUE-020](../../issues/10-2026/ISSUE-020-ke-hoach-demo-audit-ai-console/review/review-1.md)) |
| **Môi trường** | local · console `http://127.0.0.1:8090/console/` (ui/dist build 2026-10-26 19:13) · ai `6c52707` |

## Hành vi thực tế

Mở `http://127.0.0.1:8090/console/` khi chưa đăng nhập → nhập email/mật khẩu → nhập TOTP đúng → URL thành `/console/console/` và trang hiện **"Không có trang này · Về tổng quan"**. Đây là đường vào mặc định của mọi người dùng (README, phiếu audit), nên ai đăng nhập lần đầu cũng gặp trang lỗi ngay sau khi xác thực thành công.

Đăng nhập từ một trang con (`/console/settings`, `/console/vision/review`) thì không bị lặp tiền tố.

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

*(Chưa sửa.)* Kiểm sau khi sửa: lặp lại các bước tái hiện từ `/console/` và từ `/console/settings`; thêm vitest cho `saveReturnTo` với basename.
