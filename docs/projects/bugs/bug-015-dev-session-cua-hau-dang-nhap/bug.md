# 🐛 bug-015: `/auth/dev-session` cấp phiên console bằng token cố định, không cần Google hay TOTP

> **Đích:** `docs/projects/bugs/bug-015-dev-session-cua-hau-dang-nhap/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, tìm thấy khi rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed — merge vào develop qua HiTranquility/IPLMS-AI#50 (2026-10-24) / 🔴 bảo mật |
| **Ngày đóng** | 2026-10-24 |
| **Ưu tiên** | 🔴 |
| **Môi trường** | `develop@5f8e753`; endpoint có trong mọi bản build vì không có cờ môi trường nào chặn |

## Hành vi thực tế

`GET /console/api/auth/dev-session` (và `/api/auth/dev-session`) đặt cookie phiên bằng chuỗi cố định `iplms_phat_session_super_token_2026`, sau đó chuyển hướng về `/`. Chuỗi này nằm trong mã nguồn. Endpoint không kiểm môi trường (`AI_ENV`, `DEBUG`), không kiểm địa chỉ nguồn và không ghi audit. Trang đăng nhập hiện nút "Truy cập nhanh (Trưởng dự án … - Full 7 Roles)" trỏ thẳng vào endpoint này ở mọi môi trường.

Nếu bảng phiên có dòng mang `sha256` của chuỗi trên (nhãn nút "Full 7 Roles" cho thấy dòng đó đã được tạo tay), bất kỳ ai đọc được repo và tới được cổng 8090/8095 đều vào console với đủ 7 vai mà không qua Google hay TOTP. Phiên này đi vòng qua bước step-up của ADR-0051, xem được PII và promote được model. Nếu chưa có dòng đó thì endpoint chỉ là code chết, nhưng nút bấm vẫn hiện trên giao diện.

## Hành vi mong đợi

Theo IPLMS ADR-0048 và AUDIT-005, console chỉ có hai cách đăng nhập: Google + TOTP, hoặc tài khoản khẩn cấp + TOTP. Nếu cần đăng nhập nhanh để dev hoặc demo, cách đó phải tắt mặc định, chỉ bật bằng cờ cục bộ, sinh token ngẫu nhiên cho mỗi lần chạy, ghi audit và không bao giờ đi vào image production. Đề xuất cụ thể ở [SUGGESTION-001](../../suggestions/10-2026/SUGGESTION-001-dang-nhap-dev-cuc-bo-an-toan.md).

## Tái hiện

1. Mở trang đăng nhập console. Nút "Truy cập nhanh" hiện ra ([ảnh](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/01-login.png), chụp bằng REA `capture_web_screenshot` trên UI dev, không có backend thật).
2. Đọc `app/api/rest/routes/console_auth_controller.py:138-142`: route không có điều kiện nào trước `set_session_cookie(redirect, "<token cố định>")`.
3. Chưa thử gọi endpoint trên console có DB thật, vì phiên này không được đọc `.env` hay DB. Người sửa cần kiểm bảng phiên có dòng ứng với token này hay không.

## Bằng chứng

- `app/api/rest/routes/console_auth_controller.py:138-142`: route `dev_session`, token viết thẳng trong code.
- `ui/src/pages/Auth/LoginPage.tsx:108-113`: nút gọi `AUTH_ENDPOINTS.DEV_SESSION`, không kiểm `import.meta.env.DEV`.
- `ui/src/services/apiEndpoints/auth.endpoint.ts:7`.
- Thêm ở commit `9ec3afc` (2026-10-21). [AUDIT-005](../../audits/10-2026/AUDIT-005-ai-console-security-review.md) ngày 2026-10-22 kết luận "0 vi phạm" nhưng không nhắc tới route này.

## Sửa / kiểm chứng

Đã sửa trên nhánh `bugfix/bug-015-2026-10-console-auth-hardening` (2026-10-24). Chọn cách gỡ hẳn; SUGGESTION-001 (đăng nhập dev an toàn) vẫn chờ techlead duyệt, chưa làm.

- `app/api/rest/routes/console_auth_controller.py`: xoá route `GET /auth/dev-session` cùng token cố định. Trong code không còn chuỗi token nào (đã grep `*.py`, `*.ts`, `*.tsx`).
- `ui/src/pages/Auth/LoginPage.tsx`: xoá nút "Truy cập nhanh" và import `Zap`. `ui/src/pages/Auth/LoginPage.module.css`: xoá `.devSessionContainer`, `.devSessionLink`. `ui/src/services/apiEndpoints/auth.endpoint.ts`: xoá `DEV_SESSION`.
- Test mới `test/test_console_auth.py:424` (`NoDevSessionRouteTest`): `GET /console/api/auth/dev-session` và `/api/auth/dev-session` → 404, không có `set-cookie`.

Kiểm chứng: `venv/bin/python -m unittest test.test_console_auth test.test_console_db_hardening test.test_console_http` (Postgres 16 cục bộ, `AI_TEST_DATABASE_URL`): 29 test: 27 PASS, 1 skip (kiểm live DB `ai_inference`, không có DB dev), 1 FAIL có sẵn từ trước và không thuộc bug này: `test_security_headers_and_no_docs` (`/docs` trả 503 thay vì 404, bug-014). UI: `pnpm typecheck` PASS; `npx vitest run --maxWorkers=1` 12 file / 48 test PASS.

**Còn lại cho người (không làm được từ code):**
- Xoá dòng phiên có `sha256` của token cũ trong bảng phiên của DB console ở mọi môi trường (token đã nằm trong lịch sử git nên phải coi là đã lộ).
- Đính chính AUDIT-005 (kết luận "0 vi phạm" bỏ sót route này), ISSUE-004 OPEN-05. Nhánh này không sửa AUDIT-005.
