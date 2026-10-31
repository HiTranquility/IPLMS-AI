# 🐛 bug-030: Phiên "chờ MFA" tồn đọng trong danh sách Phiên đăng nhập

> **Đích:** `docs/projects/bugs/bug-030-phien-cho-mfa-ton-dong-trong-danh-sach/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** | 2026-10-31 |
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

- `app/infra/database/console_store.py`: Trong `list_active_sessions`, bổ sung điều kiện `AND s.mfa_at IS NOT NULL` để danh sách phiên hoạt động ở Settings không còn bị lẫn các phiên chưa hoàn thành xác thực hoặc đăng nhập bỏ dở.
- `app/core/console/engines/session_policy.py`: Trong `check_session`, đặt thời hạn tối đa 10 phút cho phiên chưa hoàn tất MFA (`session.get("mfa_at") is None and now - session["created_at"] > timedelta(minutes=10)`), nếu vượt quá sẽ nâng lỗi `SESSION_EXPIRED`.
- Đã bổ sung kiểm thử tại:
  - `test/test_console_auth.py`: Kiểm tra phiên chờ TOTP quá 10 phút trả về `SESSION_EXPIRED`.
  - `test/test_console_tools.py`: `test_list_sessions_delegates_and_marks_current` xác nhận `list_sessions` uỷ quyền cho `store.list_active_sessions` và gắn cờ `is_current` chính xác.
