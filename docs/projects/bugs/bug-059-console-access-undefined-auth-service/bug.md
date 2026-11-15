# 🐛 bug-059: `console_access.py` gọi tên cũ `console_auth_service` gây nổ 35 lỗi `NameError` trên `AI · CI`

> **Đích:** `docs/projects/bugs/bug-059-console-access-undefined-auth-service/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** |  |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** | 2026-11-14 |
| **Ngày báo** | 2026-11-14 |
| **Người báo** | Antigravity, khi chạy `AI · CI` hợp nhất `bug-058` vào `develop` cùng @HiTranquility (2026-11-14) |
| **Môi trường** | `ai/` (`develop` `d28b9e2`), GitHub Actions Python 3.13 |

## Hành vi thực tế

Tại `app/api/rest/console_access.py:7`, module được import dưới tên `from app.core.console import auth_service`, nhưng `require_permission` (`line 31`) và `require_any_permission` (`line 41`) trên nhánh `develop` vẫn gọi tên cũ `console_auth_service.validate_permission(permission)` sau đợt đổi tên layout `app/core`, làm nổ 35 ca `NameError: name 'console_auth_service' is not defined` trong `test_console_access`, `test_console_vision_lab`, `test_console_settings_http`, `test_console_tools` và chặn đỏ cổng `Run Python tests` của mọi PR vào `develop`.

## Hành vi mong đợi

- `require_permission` và `require_any_permission` gọi đúng `auth_service.validate_permission(permission)`.
- Toàn bộ suite `test_console_*` nạp `app.console_main` và kiểm quyền không còn lỗi `NameError`.

## Tái hiện

1. Trên `origin/develop` (`d28b9e2`), chạy `python -m unittest test/test_console_access.py`: đỏ ngay với `NameError: name 'console_auth_service' is not defined`.
2. Xem log CI run `43568839104` trên `IPLMS-AI`: `35 errors` cùng stacktrace tại `app/api/rest/console_access.py:31,41`.

## Bằng chứng

- `app/api/rest/console_access.py:7,31,41`

## Sửa / kiểm chứng

- Đổi 2 dòng `console_auth_service.validate_permission(permission)` → `auth_service.validate_permission(permission)` tại `app/api/rest/console_access.py:31,41`.
- Kiểm chứng tại máy: `test_console_access.py`, `check_core_layout.py`, `check_branch_policy.py` và `check_generated.py` đều PASS.
