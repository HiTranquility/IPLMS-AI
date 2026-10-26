# 🐛 bug-030: Phiên "chờ MFA" tồn đọng trong danh sách Phiên đăng nhập

> **Đích:** `docs/projects/bugs/bug-030-phien-cho-mfa-ton-dong-trong-danh-sach/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New |
| **Người nhận** | — |
| **Hạn** | — |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** | — |
| **Ngày báo** | 2026-10-26 |
| **Người báo** | Claude Code (lượt rà browser của ISSUE-019, [review-2](../../issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/review/review-2.md)) |
| **Môi trường** | local (stack dev `iplms-ai-dev`, console 8090) |

## Hành vi thực tế

Mỗi lần đăng nhập rồi nhập sai mã TOTP, hoặc dùng lại một mã đã dùng, danh sách Phiên đăng nhập ở trang Settings lại có thêm một phiên ở trạng thái "chờ MFA" (`mfa_at` rỗng). Các phiên này nằm lại đó, làm danh sách dài ra; trong lượt rà, danh sách đã có 29 phiên.

## Hành vi mong đợi

Phiên chưa qua MFA không hiện trong danh sách thu hồi, hoặc hiện riêng và hết hạn sau một thời gian ngắn. Phiên bị khoá vì quá số lần sai (`MAX_AUTH_FAILURES`) phải được đóng ngay, không để tồn đọng.

## Tái hiện

1. Đăng nhập console bằng mật khẩu, sang bước TOTP thì nhập sai mã (hoặc dùng lại mã vừa dùng). Lặp lại 2–3 lần.
2. Đăng nhập đúng, vào Settings → Phiên đăng nhập.
3. Thấy các phiên "chờ MFA" của những lần trước vẫn còn.

## Bằng chứng

- Luồng xác thực: `app/core/console/services/auth_service.py:129-151`. `_load(raw, require_mfa=False)` cho phép phiên chưa có MFA, sai mã thì gọi `store.fail_totp`, đúng mã thì gọi `accept_totp`. Không thấy bước dọn phiên bỏ dở ở đường nào.
- Cột `console_session.totp_failures`: `app/infra/database/console_store.py:163`.
- Quan sát trên UI: review-2 §Ngoài `ai/ui`.

## Sửa / kiểm chứng

Chưa sửa. Hướng gợi ý:
- Lọc phiên `mfa_at IS NULL` khỏi danh sách, hoặc cho chúng hạn sống ngắn.
- Đóng phiên khi `fail_totp` báo đã chạm trần.
- Viết test ở `test/test_console_auth.py`.
