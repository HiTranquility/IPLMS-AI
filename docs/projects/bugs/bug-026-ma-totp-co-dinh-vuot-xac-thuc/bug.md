# 🐛 bug-026: Mã TOTP cố định `000000` / `123456` vượt qua xác thực hai lớp và step-up

> **Đích:** `docs/projects/bugs/bug-026-ma-totp-co-dinh-vuot-xac-thuc/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-24 / Claude Code, phát hiện khi bóc i18n `MfaPage.tsx` lúc sửa bug-023 ([ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md)) |
| **Trạng thái** | ✅ Fixed — merge vào develop qua HiTranquility/IPLMS-AI#50 (2026-10-24) / 🔴 |
| **Môi trường** | `develop@5f8e753`; có từ commit `755b0a4` (2026-10-21, "ho tro dev totp code 000000") |

## Hành vi thực tế

`ConsoleAuthService._accept_code` nhận mã `000000` hoặc `123456` như mã TOTP đúng khi `type(self.store).__name__ != "FakeStore"`. Vì store thật tên `ConsoleStore`, mọi môi trường đều nhận hai mã này, kể cả production. Không có cờ môi trường, không ghi audit riêng. Đoạn mã đi cùng hai luồng:

- `verify_totp`: hoàn tất đăng nhập sau Google hoặc tài khoản khẩn cấp. Ai có được mật khẩu khẩn cấp hoặc tài khoản Google đã mời là vào được, không cần thiết bị TOTP.
- `step_up`: xác thực lại trước thao tác nhạy cảm theo ADR-0051 (khoá golden, promote model, xem PII). Phiên đã đăng nhập nhập `000000` là qua.

Điều kiện `!= "FakeStore"` khiến test đơn vị (dùng `FakeStore`) không bao giờ đi vào nhánh này, nên suite vẫn xanh. Trang MFA còn ghi gợi ý "Dev: có thể dùng 000000" ở mọi môi trường.

## Hành vi mong đợi

Theo IPLMS ADR-0048/ADR-0051: chỉ mã TOTP sinh từ secret của chính tài khoản mới được nhận. Không có mã cố định nào. Nếu cần đăng nhập nhanh khi dev, làm theo [SUGGESTION-001](../../suggestions/10-2026/SUGGESTION-001-dang-nhap-dev-cuc-bo-an-toan.md) (tắt mặc định, chỉ bật bằng cờ cục bộ, có audit).

## Tái hiện

Test `test/test_console_auth.py::ConsoleAuthServiceTest::test_no_fixed_dev_totp_code_with_real_store_class` dùng một store mang tên `ConsoleStore`. Chạy trên code `develop`: FAIL (mã `000000` được nhận). Chạy sau khi sửa: PASS.

## Bằng chứng

- `app/core/console/services/auth_service.py:145-147` (trước khi sửa).
- `ui/src/pages/Auth/MfaPage.tsx:92`: gợi ý mã dev.
- Cùng đợt với cửa hậu dev-session ([bug-015](../bug-015-dev-session-cua-hau-dang-nhap/bug.md)). [AUDIT-005](../../audits/10-2026/AUDIT-005-ai-console-security-review.md) cũng không nhắc tới.

## Sửa / kiểm chứng

Sửa 2026-10-24 trên nhánh `bugfix/bug-015-2026-10-console-auth-hardening` (cùng nhóm cửa hậu đăng nhập với bug-015), tác giả HiTranquility:

- `app/core/console/services/auth_service.py`: xoá nhánh nhận mã cố định.
- `ui/src/pages/Auth/MfaPage.tsx`: gợi ý lấy từ i18n `mfa.otpHint` (VI/EN), không còn nhắc mã dev.
- Test hồi quy mới như mục Tái hiện. Đã chạy ngược trên code cũ để xác nhận test bắt được lỗi.

Kiểm: `python -m unittest test.test_console_auth` 23/23 PASS. UI: `pnpm typecheck` PASS, vitest 48/48 PASS.

Việc cho người vận hành: rà nhật ký `auth.*` / `console_session` từ 2026-10-21 tới khi deploy bản sửa, tìm phiên hoàn tất MFA hoặc step-up bất thường. Đính chính AUDIT-005 cùng bug-015.
