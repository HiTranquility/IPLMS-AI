# 🐛 bug-055: CI `AI · CI` dừng ở bước khởi tạo Postgres vì thiếu `POSTGRES_PASSWORD`, unittest và kiểm khuôn không bao giờ chạy

> **Đích:** `docs/projects/bugs/bug-055-ci-thieu-postgres-password-test-khong-chay/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🛠️ Fixing |
| **Người nhận** | @HiTranquility |
| **Hạn** |  |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** |  |
| **Ngày báo** | 2026-11-03 |
| **Người báo** | Claude Code, khi rà lỗi còn tồn (2026-11-03) |
| **Môi trường** | GitHub Actions, `develop` `a7de8d0` |

## Hành vi thực tế

Job "Run Python tests" của workflow `AI · CI` dừng ở bước "Initialize Postgres databases and vector extension". `python -m app.script.harden_console_db` ném lỗi:

```
RuntimeError: Thiếu biến môi trường POSTGRES_PASSWORD hoặc AI_DB_PASSWORD. Đặt giá trị trong môi trường chạy script, không có giá trị mặc định.
```

Các bước sau ("Run unit tests", "Compile Python sources", "Check core layout") bị bỏ qua. Mọi lượt chạy trên `develop` từ 2026-10-31 đều đỏ, nên CI không chặn được hồi quy nào.

## Hành vi mong đợi

Bước khởi tạo DB qua được, unittest và `script/check_core_layout.py` chạy trên mọi PR và push vào `develop`.

## Tái hiện

1. Mở bất kỳ lượt `AI · CI` nào trên `develop`, ví dụ run `41453759540` (2026-11-02, `946a4cb`).
2. Đọc log bước "Initialize Postgres databases and vector extension": lỗi trên.

## Bằng chứng

- `app/script/harden_console_db.py:45`: `admin_pw = _require_env("POSTGRES_PASSWORD", "AI_DB_PASSWORD")`. Bắt buộc từ commit `b85d649` (bug-016, bỏ mật khẩu mặc định trong code).
- `.github/workflows/ci.yml`: `POSTGRES_PASSWORD` chỉ nằm trong `services.postgres.env` (dòng 27), là env của **container** Postgres, không tới được các bước của job. `env:` cấp job có `CI_DB_PASSWORD`, `AI_CONSOLE_DB_PASSWORD`, `AI_INFERENCE_DB_PASSWORD` nhưng không có `POSTGRES_PASSWORD`/`AI_DB_PASSWORD`.
- Lỗi bị che trước 2026-10-28 vì job GitHub không khởi động (lỗi thanh toán tài khoản). Khi CI chạy lại được thì bước này đỏ ở mọi lượt.

## Sửa / kiểm chứng

- `.github/workflows/ci.yml`: bước "Initialize Postgres databases and vector extension" thêm `env: POSTGRES_PASSWORD: ${{ env.CI_DB_PASSWORD }}`. Cùng giá trị với mật khẩu container, chỉ cấp cho đúng bước cần, không đổi env của bước test.
- Kiểm tại máy: YAML parse được; `harden_console_db.get_db_urls()` với bộ biến giống bước CI (có `POSTGRES_PASSWORD`) trả URL admin/inference đúng; thiếu biến thì vẫn ném lỗi như cũ.
- Kiểm thật: lượt `AI · CI` của PR sửa lỗi qua được bước khởi tạo DB và chạy tới unittest.
