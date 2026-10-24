# 🐛 bug-016: `harden_console_db.py` có mật khẩu mặc định thật cho role `ai_console` viết thẳng trong code

> **Đích:** `docs/projects/bugs/bug-016-mat-khau-db-console-mac-dinh-trong-code/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, tìm thấy khi đọc code console trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | 🆕 New / 🔴 bảo mật (lộ secret) |
| **Môi trường** | `develop@5f8e753`, thêm ở commit `ae47ad2` |

## Hành vi thực tế

`app/script/harden_console_db.py:72` gọi `os.environ.get("AI_CONSOLE_DB_PASSWORD", "***REDACTED***")`. Giá trị mặc định là một mật khẩu cụ thể, không phải placeholder, và đã nằm trong lịch sử git. Khi người chạy script quên đặt biến môi trường, script vẫn chạy tiếp, rồi `CREATE ROLE` hoặc `ALTER ROLE ai_console WITH PASSWORD` bằng giá trị này (dòng 73-78). DB console, nơi chứa PII và audit, khi đó có mật khẩu mà ai đọc repo cũng biết. Script cũng không báo gì cho người chạy.

## Hành vi mong đợi

Thiếu `AI_CONSOLE_DB_PASSWORD` thì script dừng với lỗi rõ ràng, giống cách nó đang xử lý `inference_pw` (truyền vào qua tham số), và không có giá trị mặc định nào. Mật khẩu đã lộ phải được coi là đã mất: đổi trên mọi môi trường từng chạy script, rồi quét secret toàn lịch sử.

## Tái hiện

Đọc `app/script/harden_console_db.py:72-78`. Không chạy script, vì nó ghi vào DB dùng chung.

## Bằng chứng

- `app/script/harden_console_db.py:72` (giá trị đã che trong hồ sơ này).
- `git log -- app/script/harden_console_db.py`: file có từ commit `ae47ad2` (2026-10-22).
- `script/scan_secrets.py` ở gốc chỉ quét dòng sắp push, nên không bắt được secret đã có sẵn trong lịch sử.

## Sửa / kiểm chứng

Chưa sửa. Cần: bỏ giá trị mặc định và fail-closed khi thiếu biến; đổi mật khẩu role `ai_console` ở mọi môi trường đã chạy script; thêm test đơn vị cho trường hợp thiếu biến môi trường.
