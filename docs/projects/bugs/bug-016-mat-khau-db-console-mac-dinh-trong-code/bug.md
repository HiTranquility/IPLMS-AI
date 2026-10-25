# 🐛 bug-016: `harden_console_db.py` có mật khẩu mặc định thật cho role `ai_console` viết thẳng trong code

> **Đích:** `docs/projects/bugs/bug-016-mat-khau-db-console-mac-dinh-trong-code/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, tìm thấy khi đọc code console trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed — merge vào develop qua HiTranquility/IPLMS-AI#50 (2026-10-24) / 🔴 bảo mật (lộ secret) |
| **Ngày đóng** | 2026-10-24 |
| **Ưu tiên** | 🔴 |
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

Đã sửa trên nhánh `bugfix/bug-015-2026-10-console-auth-hardening` (2026-10-24, gom chung với bug-015 theo chủ dự án duyệt).

- `app/script/harden_console_db.py:30`: thêm `_require_env(...)`; thiếu biến thì `RuntimeError` nêu tên biến, không có giá trị dự phòng.
- Cùng file có thêm 3 giá trị mặc định khác viết trong code (mật khẩu admin Postgres, URL admin có mật khẩu, mật khẩu `ai_inference` ở hai chỗ). Đây cùng loại lỗi nên bỏ luôn: dòng 45, 47, 52, 199. `AI_CONSOLE_DB_PASSWORD` giờ được kiểm **trước** khi kết nối DB (dòng 61), nên thiếu biến thì script không đụng tới DB.
- Test mới `test/test_console_db_hardening.py:41` (thiếu `AI_CONSOLE_DB_PASSWORD` → lỗi, `psycopg2.connect` không được gọi) và `:49` (thiếu mật khẩu admin, mật khẩu `ai_inference` hoặc URL admin → lỗi).

Kiểm chứng: `venv/bin/python -m unittest test.test_console_auth test.test_console_db_hardening test.test_console_http` (Postgres 16 cục bộ, `AI_TEST_DATABASE_URL`): 29 test: 27 PASS, 1 skip (kiểm live DB `ai_inference`, không có DB dev), 1 FAIL có sẵn từ trước và không thuộc bug này: `test_security_headers_and_no_docs` (`/docs` trả 503 thay vì 404, bug-014). UI: `pnpm typecheck` PASS; `npx vitest run --maxWorkers=1` 12 file / 48 test PASS.

**Còn lại cho người:**
- Đổi mật khẩu role `ai_console` và `ai_inference` trên mọi môi trường từng chạy script, vì các giá trị cũ đã nằm trong lịch sử git.
- Mật khẩu dev giống giá trị cũ của admin vẫn xuất hiện ở `.github/workflows/ci.yml` (DB dịch vụ tạm của CI) và `docker-compose.yml:119`. Đây là cấu hình dev/CI ngoài phạm vi script này, cần người quyết có đổi sang biến/secret hay không.
