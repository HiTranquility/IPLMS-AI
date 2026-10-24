# review-2 — Sửa 12 bug từ lượt rà `ai/ui` và nối API thật, 2026-10-24

> Hồ sơ cha: [ISSUE-004](../issue.md) · Trước đó: [review-1](review-1.md) · Người làm: HiTranquility (cùng Claude Code) · Chủ dự án chốt: OPEN-01 = backend nhận tham số; OPEN-02 = lưu cờ ảnh vào DB; OPEN-03 = báo lỗi thật + nhãn MÔ PHỎNG; nối API thật nơi có service.

## Kết quả

Đã sửa đủ 11 bug review-1 ghi lại (bug-015 … bug-025), cộng **bug-026** phát hiện trong lúc sửa: mã TOTP cố định `000000`/`123456` vượt MFA và step-up ở mọi môi trường. Ba studio có service thật đã nối API thật. Kiểm trên nhánh tổng hợp:

- Backend: 104 test pass trên Postgres 16 cục bộ.
- UI: 72/72 test pass, typecheck sạch.
- Browser: 66 màn, 0 tràn ngang, 0 chữ dưới AA, 0 lỗi JS.

## Nhánh và thứ tự merge

Đã merge vào `develop` ngày 2026-10-24 theo đúng thứ tự: ISSUE-004 #49 → #50 → #51 → #52 → #53, sau đó ISSUE-005. CI GitHub Actions của repo đang hỏng toàn bộ (job dừng sau khoảng 3 giây, không có log, kể cả PR #48 trước đó), nên mọi kiểm chứng chạy local như ghi dưới.


| Nhánh | Bug | Ghi chú |
|---|---|---|
| `bugfix/bug-015-2026-10-console-auth-hardening` | 015, 016, 026 | Bảo mật, nên merge trước |
| `bugfix/bug-017-2026-10-chat-studio-contract` | 017, 018 + nối API thật | Đổi hợp đồng `/tools/copilot*` (thêm 3 trường tuỳ chọn), thêm route `/tools/anpr/recognize`, `/tools/vision/verify-match`, `/tools/knowledge/documents`, `engines` trong `/tools/system` |
| `bugfix/bug-019-2026-10-audit-export-and-actions` | 019, 020 | |
| `bugfix/bug-021-2026-10-console-ui-polish` | 021, 022, 023, 024, 025 | Đã gộp sẵn ba nhánh trên (bug-023 đụng hầu hết file của chúng), nên **merge cuối**. Thêm cột `vision_label.quality_flags` (migrate tại chỗ, idempotent) |

Cả bốn nhánh đều tách từ `docs/ISSUE-004-2026-10-ai-console-ui-review` (đã gồm hồ sơ bug), nên PR ISSUE-004 nên vào `develop` trước.

## Bug

| Mã | Mức | Đã làm | Trạng thái |
|---|---|---|---|
| BUG-01 bug-015 | 🔴 | Gỡ route dev-session + nút, test 404 | ✅ chờ PR. Còn xoá phiên cũ trong DB |
| BUG-02 bug-016 | 🔴 | Bỏ 4 giá trị mặc định chứa mật khẩu, fail-closed | ✅ chờ PR. Còn đổi mật khẩu ở mọi môi trường |
| BUG-12 bug-026 (mới) | 🔴 | Gỡ mã TOTP cố định, test hồi quy (đỏ trên code cũ) | ✅ chờ PR. Còn rà nhật ký phiên từ 2026-10-21 |
| BUG-03 bug-017 | 🔴 | `AskIn` nhận 3 tham số có biên, không nới guard; sửa thêm UI đọc sai trường SSE | ✅ chờ PR |
| BUG-04 bug-018 | 🔴 | 7 chỗ hết bịa. ANPR, Anti-Fraud, tri thức, chẩn đoán nối API thật | ✅ chờ PR. Dispute/Forecast vẫn MÔ PHỎNG |
| BUG-05 bug-019 | 🟠 | CSV escape + chặn formula injection | ✅ chờ PR |
| BUG-06 bug-020 | 🟡 | Từ điển mã server + test đối chiếu Python | ✅ chờ PR |
| BUG-07 bug-021 | 🟡 | `fmtDayMonth` | ✅ chờ PR |
| BUG-08 bug-022 | 🟡 | Lưu `quality_flags` (DB + API + UI + hàng duyệt) | ✅ chờ PR |
| BUG-09 bug-023 | 🟡 | ~300 khoá i18n, test chặn chữ viết cứng | ✅ chờ PR |
| BUG-10 bug-024 | 🟠 | Tools 768 + `/vision`, `/members` 375 | ✅ chờ PR |
| BUG-11 bug-025 | 🟠 | Token + 22 chỗ accent + RoleBadge | ✅ chờ PR |

### Cần người quyết hoặc làm tay

| Mã | Việc | Ai |
|---|---|---|
| OPEN-04 | Xoá dòng phiên của token dev-session cũ; đổi mật khẩu role `ai_console`/`ai_inference`; rà nhật ký MFA/step-up từ 2026-10-21 | Người vận hành DB console |
| OPEN-05 | Đính chính AUDIT-005 (không nêu bug-015, bug-016, bug-026) | Chủ dự án / review độc lập |
| OPEN-06 | Mật khẩu dev (đã che) còn trong `.github/workflows/ci.yml` và `docker-compose.yml:119`: chuyển sang secret? | Techlead |
| OPEN-07 | bug-014 (`/docs` 200/503 thay vì 404) vẫn mở: chốt 404 hay sửa test | Techlead |

## Đã kiểm thế nào

| Bước | Lệnh / công cụ | Kết quả |
|---|---|---|
| Backend console | `python -m unittest test.test_console_auth test_console_db_hardening test_console_tools test_console_copilot_lab test_console_vision_lab test_console_audit_codes test_console_member_service test_console_access test_rag_pipeline test_llm_factory test_output_guard`, venv tạm (được phép cài), `AI_TEST_DATABASE_URL` = Postgres 16 cục bộ | 104 test PASS (1 skip: DB `ai_inference` thật) |
| Backend còn đỏ sẵn | `test_console_http::test_security_headers_and_no_docs` | FAIL như trước khi sửa (bug-014) |
| Thiếu stub gRPC | `test_console_vision_import`, `test_copilot_usage`, `test_model_policy` | Lỗi môi trường, giống trên code cũ |
| UI | `pnpm typecheck`; `npx vitest run --maxWorkers=1` | PASS; 17 file / 72 test |
| Browser | Playwright + Chromium 1243, UI dev + `mock_console_api.py`, 11 màn × 375/768/1280 × sáng/tối | 0 tràn ngang, 0 chữ dưới 4.5:1 (3:1 cho chữ lớn), 0 lỗi JS |
| EN | 10 trang ở chế độ EN | Chữ giao diện không còn tiếng Việt. Phần còn thấy là dữ liệu của API giả |
| Chuỗi cung ứng | `pnpm audit --prod`; `pip-audit` trên venv tạm | UI prod 0. Python: `protobuf 5.29.5` có PYSEC-2026-1805 (bản vá 5.29.6), repo đang pin. Gom vào lượt bump của CHORE tháng |
| Chưa chạy | ANPR với weights thật, LLM thật, đăng nhập Google + TOTP thật | NOT RUN: không có weights/tài khoản trong môi trường này |
