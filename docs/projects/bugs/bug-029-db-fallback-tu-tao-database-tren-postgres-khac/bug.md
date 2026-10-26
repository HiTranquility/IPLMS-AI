# 🐛 bug-029: Fallback kết nối DB sang cổng 5432 rồi tự `CREATE DATABASE` trên một Postgres khác

> **Đích:** `docs/projects/bugs/bug-029-db-fallback-tu-tao-database-tren-postgres-khac/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🛠️ Fixing — đã sửa trên nhánh `bugfix/bug-029-2026-10-db-fallback-tu-tao-database`, chờ PR |
| **Người báo** | Auditor AUDIT-006 (finding A-23, vòng 1–3); mở hồ sơ trong đợt [ISSUE-019](../../issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md) |
| **Môi trường** | local (máy dev có nhiều Postgres); nhánh code áp cho URL của mọi môi trường |
| **Người nhận** | @HiTranquility |
| **Hạn** | — |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | — |

## Hành vi thực tế

`connect_with_fallback` thử lần lượt các ứng viên cổng `[custom_port, 5435, 5432]`. Khi ứng viên kết nối được nhưng database chưa tồn tại, code **tự tạo database** ngay trên ứng viên đó. Hậu quả: trên máy có Postgres khác ở 5432 (ví dụ Postgres của backend hay một dự án khác), nếu container AI ở 5435 chưa lên, AI service tạo DB và bảng, rồi ghi tri thức, telemetry và dữ liệu console vào nhầm Postgres mà không báo gì.

## Hành vi mong đợi

- Chỉ tự tạo DB khi ứng viên trùng URL đã cấu hình, hoặc là cổng map của chính DB AI (`AI_DB_HOST_PORT`). Bản sửa không thêm cờ dev: xem mục Sửa.
- Ứng viên fallback chỉ được dùng để kết nối tới DB đã có; không tạo DB trên đó.
- Mỗi khi dùng ứng viên khác URL cấu hình thì log warning (URL đã che mật khẩu).

## Tái hiện

1. Máy dev có Postgres native ở 5432 (user có quyền CREATEDB), container `database-vector` ở 5435 đang tắt.
2. Đặt `AI_DATABASE_URL` trỏ `database-vector:5432/iplms_knowledge` như `.env.example`.
3. Khởi động AI service → `iplms_knowledge` được tạo trên Postgres 5432.

Chưa chạy trên DB thật (theo AUDIT-006 §5, DB thật NOT RUN); chứng minh bằng đọc code ở dưới.

## Bằng chứng

- `app/infra/database/db_connection.py:61`: `target_ports = [custom_port, 5435, 5432]`.
- `app/infra/database/db_connection.py:107-130`: `_ensure_database_exists` chạy `CREATE DATABASE`.
- `app/infra/database/db_connection.py:176-178`: gọi `_ensure_database_exists(cand_url, …)` cho **mọi** ứng viên khi gặp lỗi "does not exist".
- AUDIT-006 [audit-2](../../issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/review/audit-2.md) A-23, [audit-3](../../issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/review/audit-3.md): vẫn Open.

## Sửa / kiểm chứng

- `app/infra/database/db_connection.py`, hàm `_may_create_database`: chỉ tự tạo DB khi ứng viên **trùng URL cấu hình**, hoặc chạy đúng **cổng map của chính DB AI** (`AI_DB_HOST_PORT`, mặc định 5435). Ứng viên khác, ví dụ `127.0.0.1:5432` của một Postgres khác, chỉ được dùng để kết nối tới DB đã có.
  - Quyết định: không thêm cờ môi trường mới, vì tự tạo đúng DB của AI là tiện lợi mà đợt WIP chủ ý giữ khi chạy native.
- Cùng hàm còn lộ **mật khẩu ra log**: log "Database Fallback" in nguyên `netloc`, câu lỗi cuối in cả danh sách ứng viên. Cả hai giờ đi qua `_redact_url`; log fallback nâng lên mức warning.
- Test: `test/test_db_connection_fallback.py`, 4 ca, `psycopg2.connect` giả lập:
  - ứng viên 5432 thiếu DB thì không tạo;
  - cổng map 5435 thì vẫn tạo;
  - kiểm bảng luật `_may_create_database`;
  - log fallback không chứa mật khẩu.
- Chưa chạy trên Postgres thật có hai instance.
- Deferred (P3, [review/audit-1.md](review/audit-1.md)):
  - A-1: store gán lại `self.db_url` bằng URL fallback, nên lần sau URL đó được coi là "URL cấu hình".
  - A-4: `AI_DB_HOST_PORT` đọc từ `os.environ`, không qua `get_config`.
  - A-5: `_redact_url` không che mật khẩu nằm trong query string.
