# 🐛 bug-014: Console trả SPA 200 cho `/docs`, test "không có docs" đỏ

> **Đích:** `docs/projects/bugs/bug-014-console-docs-tra-spa-thay-vi-404/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code (phát hiện khi kiểm [bug-013](../bug-013-vision-demo-seed-khong-chan-production/bug.md)) |
| **Trạng thái** | ✅ Fixed |
| **Môi trường** | local, `develop@534e0f8` |

## Hành vi thực tế

Trước khi sửa: `GET /docs` trên console trả 200 (nội dung `index.html` của SPA fallback). `test/test_console_http.py:134` chờ 404 nên FAIL (`AssertionError: 404 != 200`).

## Hành vi mong đợi

Đường dẫn nhạy cảm/docs (`/docs`, `/docs/{path}`, `/redoc`, `/redoc/{path}`, `/openapi.json`, và các tiền tố `/console/docs`, v.v.) phải trả 404 dù có SPA fallback, tuân thủ nguyên tắc không lộ Swagger / 0 CDN (ADR-0048 §5).

## Tái hiện

`AI_TEST_DATABASE_URL=… python -m unittest test.test_console_http` trên `develop` → `AssertionError: 404 != 200`.

## Bằng chứng

`app/console_main.py` `@app.get("/{path:path}")` bắt mọi đường dẫn; `docs_url=None` ở `app/console_main.py:29` không đăng ký route của Swagger nên request rơi vào route catch-all SPA trả `index.html`.

## Sửa / kiểm chứng

- `app/console_main.py`: Khai báo explicit 404 handler cho các path:
  - `/docs`, `/docs/{_path:path}`
  - `/redoc`, `/redoc/{_path:path}`
  - `/openapi.json`
  - `/console/docs`, `/console/docs/{_path:path}`, `/console/redoc`, `/console/openapi.json`
- `test/test_console_http.py`: Kiểm tra trả về 404 cho `/docs`, `/openapi.json`, và `/redoc`.
- Chạy kiểm thử: `docker exec -i iplms-ai-dev-console-1 python -` với `test_console_http.py` → 2/2 tests PASS.
