# 🏷️ ISSUE-019: Đợt WIP AI Console: trang Settings, gom danh sách bãi, seed demo và dọn finding AUDIT-006

> **Đích:** `docs/projects/issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress |
| **Người phụ trách** | HiTranquility (tích hợp); Claude Code viết phần sửa finding AUDIT-006 |
| **Phạm vi** | `ai/`: API console (`app/api/rest`, `app/core/console`), config, `app/infra/llm`, `app/infra/database`, `ui/`, test |
| **Nhánh** | `feature/ISSUE-019-2026-10-console-settings-audit-006` |
| **Người nhận** | @HiTranquility |
| **Hạn** | — |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | — |

## Mục tiêu

Hợp thức hoá đợt WIP console ngày 2026-10-25, vốn đã sửa khoảng 100 file mà chưa có hồ sơ. Nội dung đợt WIP gồm:
- trang **Settings**: phần cứng/engine, ngưỡng AI, phiên đăng nhập, ứng viên eval;
- gom danh sách bãi về `ui/src/constants/parkingLots.ts`;
- script `app/script/seed_console_demo.py`;
- Ollama làm provider LLM mặc định;
- fallback kết nối DB;
- chỉnh UI cho Copilot Lab, LabelStudio và ForecastSimulator.

Đợt này cũng sửa các finding P0/P1 mà [AUDIT-006](../../../audits/10-2026/AUDIT-006-console-wip-2026-10-25.md) tìm ra qua 3 vòng audit.

## 📋 Việc trên BOARD

| Việc | Người nhận | Hạn | Ưu tiên | Trạng thái | Ghi chú |
|---|---|---|---|---|---|
| Soát PR ISSUE-019: soát lại chéo audit-6 và chạy convention audit cho phần UI của review-2, kiểm UI/UX theo quy trình (375/1024px × sáng/tối, a11y, VI/EN) và đối chiếu đủ conventions (AI_CONVENTIONS, `ui/DESIGN.md`, `check_diff`) | Dương | — | 🟠 | 📝 Đã giao — chưa bắt đầu | Chủ dự án giao 2026-10-26. Ghi kết quả vào `review/audit-6.md`; tài khoản test console tạo theo review-2 |
| Sửa `docs/projects/KHOA_MODULE_GUIDE.md` cho khớp việc AI không còn tự bật llama-server: `:35`, `:160`, `:240`, `:289-292`, `:535`; cùng `AI_GUIDE.md:315`, `AI_USAGE.md:34`, `:79`, `:102`. Chốt xoá hay giữ `app/infra/llm/llama_server_manager.py` (không còn chỗ gọi) | Khoa | — | 🟡 | 📝 Đã giao — chưa bắt đầu | Từ A-41; `KHOA_MODULE_GUIDE.md` đang có thay đổi chưa commit của phiên khác, sửa sau khi file đó được commit |

## Tiêu chí chấp nhận

- [x] Không còn finding P0/P1 Open (theo [audit-3](review/audit-3.md): 15 Verified, cộng A-54/A-55/A-48/A-56 sửa sau vòng 3).
- [x] Settings: ngưỡng lưu qua `ReasonAction` (TOTP + lý do); provider chỉ đổi giữa `ollama`/`local`; `llm_base_url` không đổi được qua API; UI báo đúng là inference cần khởi động lại.
- [x] Override runtime tách thành `app/config/runtime_override_config.py`, có kẹp biên; file hỏng thì bỏ cả file; test không ghi file thật.
- [x] A-39 (chủ dự án chọn B): mặc định `llm_provider=ollama`, DESIGN.md / `.env.example` / README Copilot khớp code.
- [x] `python -m unittest discover -s test`: 554 OK, 34 skip · `npx tsc --noEmit` PASS · vitest 93/93 PASS · `check_diff.py` 0 FAIL.
- [ ] Kiểm browser các màn sau đăng nhập (Settings với luồng TOTP, Copilot Lab, LabelStudio, Forecast) ở 375/1024 px × sáng/tối. **NOT RUN:** cần tài khoản test có TOTP.
- [x] P2 còn mở được sửa hoặc ghi `Deferred` kèm hồ sơ. A-11/12, A-25, A-40, A-53 đã Verified ở [audit-4](review/audit-4.md). Ngày 2026-10-26 sửa thêm: A-7 (seed bỏ số metrics bịa và bỏ promote, gắn `[DEMO]`, `seed_console_demo.py:552-558`), A-37 (`copilot_lab_service.py`: che PII bằng `redact`, cắt theo hạn lưu telemetry, audit không chép câu hỏi), A-41 (`llm_factory.py:161-165`: dò llama-server qua `asyncio.to_thread`). A-23 chuyển sang [bug-029](../../../bugs/bug-029-db-fallback-tu-tao-database-tren-postgres-khac/bug.md). Kiểm: unittest 569 OK, 34 skip · `check_diff` 0 FAIL. Auditor soát delta: [audit-6](review/audit-6.md) ✅ (mở 4 P3: A-70…A-73). A-7 chưa chạy script trên DB thật.
- [x] A-22: chủ dự án chọn B (2026-10-26) → [ADR-0001](../../adrs/10-2026/0001-fallback-khong-pgvector-chi-cho-dev.md). Fallback chỉ chạy khi `AI_EMBEDDING_ALLOW_NO_PGVECTOR=true`, mặc định tắt (`pgvector_client.py`, `embedding_config.py`); test `test/test_pgvector_fallback_flag.py` 3/3.

## Kế hoạch

1. Commit WIP console cùng phần sửa AUDIT-006 → kiểm: unittest, tsc, vitest, check_diff (đã PASS ngày 2026-10-25).
2. Kiểm browser theo cổng chất lượng L1–L8 → kiểm: ảnh chụp và số đo trong `evidence/`.
3. Sửa hoặc hoãn từng P2 → kiểm: auditor soát delta.
4. PR vào `develop`.

## Ngoài phạm vi, đã tách hồ sơ

- [bug-028](../../../bugs/bug-028-forecast-id-bai-lech-area-key/bug.md): id bãi trên UI lệch `area_key` của Gold lake, nên Forecast luôn chạy baseline.
- [bug-029](../../../bugs/bug-029-db-fallback-tu-tao-database-tren-postgres-khac/bug.md): fallback DB sang cổng 5432 rồi tự `CREATE DATABASE` (A-23).
- SUGGESTION-006 (lộ trình hoàn thiện console) đi nhánh riêng theo IPLMS ADR-0059.
- Rename đang stage `ISSUE-007-console-tools-and-knowledge-management` → `ISSUE-011-…` **trùng mã** với `ISSUE-011-phan-ai-cua-iplms-audit-004` ở nhánh khác. Phải đổi sang mã kế tiếp trên nhánh chore tháng; không gộp vào nhánh này.
- Seed `seed_console_demo.py` mục 4: lý do đề xuất chính sách ngưỡng ("100% mẫu… đều đọc chính xác") cũng là số tự đặt. Ngoài phạm vi A-7, chưa sửa; auditor vòng sau ghi thành finding.
- Ngoài phạm vi, auditor ghi nhận: `docker-compose.yml:120` bật `AI_CONSOLE_DEMO_SEED_ENABLED=true` ở compose base, trái `DESIGN.md:13`.

## Hồ sơ liên quan

- [AUDIT-006](../../../audits/10-2026/AUDIT-006-console-wip-2026-10-25.md) · [audit-2](review/audit-2.md) · [audit-3](review/audit-3.md)
- [console tools & knowledge](../ISSUE-007-console-tools-and-knowledge-management/issue.md) (đã merge qua PR #71), [ISSUE-008](../ISSUE-008-console-access-policy-regression-tests/issue.md) (test quyền 7 vai)
- IPLMS ADR-0048 (quyền console, step-up), ADR-0051 (accept policy), ADR-0029 (guardrail LLM)
