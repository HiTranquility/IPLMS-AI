# 🐛 bug-014: Console trả SPA 200 cho `/docs`, test "không có docs" đỏ

> **Đích:** `docs/projects/bugs/bug-014-console-docs-tra-spa-thay-vi-404/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code (phát hiện khi kiểm [bug-013](../bug-013-vision-demo-seed-khong-chan-production/bug.md)) |
| **Trạng thái** | 🆕 New / 🟡 |
| **Môi trường** | local, `develop@534e0f8` |

## Hành vi thực tế

`GET /docs` trên console trả 200 (nội dung `index.html` của SPA). `test/test_console_http.py:134` chờ 404 nên FAIL.

## Hành vi mong đợi

Cần chốt một trong hai: (a) đường dẫn nhạy cảm (`/docs`, `/redoc`, `/openapi.json`) trả 404 dù có SPA fallback; hoặc (b) chấp nhận SPA fallback và sửa test chỉ kiểm "không phải Swagger".

## Tái hiện

`AI_TEST_DATABASE_URL=… python -m unittest test.test_console_http` trên `develop` (chưa có thay đổi bug-013) → `AssertionError: 404 != 200`.

## Bằng chứng

`app/console_main.py:98` `@app.get("/{path:path}")` (thêm ở `cb42e9c`, ISSUE-003) bắt mọi đường dẫn; `docs_url=None` ở `app/console_main.py:29` vẫn đúng nên không lộ Swagger, chỉ test lệch.

## Sửa / kiểm chứng

Chưa sửa.
