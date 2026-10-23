# 🌱 SUGGESTION-002: API giả có hợp đồng và smoke test browser 7 vai × 3 viewport × 2 theme cho `ai/ui`

> **Đích:** `docs/projects/suggestions/10-2026/SUGGESTION-002-mock-api-va-ma-tran-browser-cho-ui.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🔄 REVIEWING |
| **Ngày** | 2026-10-23 |
| **Người đề xuất** | Claude Code ([ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md)) |
| **Techlead duyệt** | @HiTranquility — ⏳ chờ |
| **Làm trước khi duyệt?** | Có thể: không đổi API/schema, chỉ thêm công cụ test. Nếu cần package mới (Playwright, MSW) thì phải hỏi chủ dự án trước khi cài |
| **Phạm vi** | `ai/ui` |

## Đề xuất

1. Tạo một API giả có hợp đồng, sinh từ OpenAPI của `console_main` (hoặc viết tay như [mock_console_api.py](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/mock_console_api.py)). Dữ liệu đủ cho 7 vai và đủ các ca lỗi 401/403/404/422/500/timeout.
2. Viết một kịch bản smoke chạy trên mỗi tổ hợp vai × viewport (375/768/1280) × theme (light/dark). Mỗi lượt chụp ảnh, ghi lỗi console và request 4xx/5xx ngoài dự kiến, kiểm tràn ngang. Đây là các ngưỡng L5 của quality-gate.
3. Thêm test hợp đồng: body mà UI gửi phải validate được bằng model Pydantic của route. Nếu có test này thì đã bắt được [bug-017](../../bugs/bug-017-chat-studio-luon-422/bug.md).

## Vấn đề nó giải quyết

Test UI hiện có (48/48 xanh) đều mock `fetch` theo ý của component, nên lệch hợp đồng ([bug-017](../../bugs/bug-017-chat-studio-luon-422/bug.md)) và nhánh "bịa khi lỗi" ([bug-018](../../bugs/bug-018-ui-bia-ket-qua-khi-api-loi/bug.md)) đều lọt. Muốn chạy UI thật thì cần DB, Google và TOTP, nên không ai chạy được nhanh.

## Phạm vi

- Trong: mock, kịch bản smoke, test hợp đồng, job CI `ui` (đã có ở `.github/workflows/ci.yml:80`).
- Ngoài: E2E với backend thật.

## Bằng chứng / tham khảo

- Lượt rà ngày 2026-10-23 dùng API giả, REA và CDP chụp đủ 11 màn hình ([ISSUE-004 review-1](../../issues/10-2026/ISSUE-004-ai-console-ui-review/review/review-1.md)).
- Chạy `vitest` song song trên máy dev bị timeout khi khởi động worker. Chạy với `--maxWorkers=1` thì xanh. Nên cố định số worker trong `vite.config.ts`.

## Bước tiếp theo

Duyệt, rồi mở ISSUE. Gợi ý giao Phát (UI) phối hợp với Dương (test quyền 7 vai).
