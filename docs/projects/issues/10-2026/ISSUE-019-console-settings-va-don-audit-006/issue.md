# 🏷️ ISSUE-019: Đợt WIP AI Console: trang Settings, gom danh sách bãi, seed demo và dọn finding AUDIT-006

> **Đích:** `docs/projects/issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress |
| **Người phụ trách** | HiTranquility (tích hợp); Claude Code viết phần sửa finding AUDIT-006 |
| **Phạm vi** | `ai/`: API console (`app/api/rest`, `app/core/console`), config, `app/infra/llm`, `app/infra/database`, `ui/`, test |
| **Nhánh** | `feature/ISSUE-019-2026-10-console-settings-audit-006` |

## Mục tiêu

Hợp thức hoá đợt WIP console ngày 2026-10-25, vốn đã sửa khoảng 100 file mà chưa có hồ sơ. Nội dung đợt WIP gồm:
- trang **Settings**: phần cứng/engine, ngưỡng AI, phiên đăng nhập, ứng viên eval;
- gom danh sách bãi về `ui/src/constants/parkingLots.ts`;
- script `app/script/seed_console_demo.py`;
- Ollama làm provider LLM mặc định;
- fallback kết nối DB;
- chỉnh UI cho Copilot Lab, LabelStudio và ForecastSimulator.

Đợt này cũng sửa các finding P0/P1 mà [AUDIT-006](../../../audits/10-2026/AUDIT-006-console-wip-2026-10-25.md) tìm ra qua 3 vòng audit.

## Tiêu chí chấp nhận

- [x] Không còn finding P0/P1 Open (theo [audit-3](review/audit-3.md): 15 Verified, cộng A-54/A-55/A-48/A-56 sửa sau vòng 3).
- [x] Settings: ngưỡng lưu qua `ReasonAction` (TOTP + lý do); provider chỉ đổi giữa `ollama`/`local`; `llm_base_url` không đổi được qua API; UI báo đúng là inference cần khởi động lại.
- [x] Override runtime tách thành `app/config/runtime_override_config.py`, có kẹp biên; file hỏng thì bỏ cả file; test không ghi file thật.
- [x] A-39 (chủ dự án chọn B): mặc định `llm_provider=ollama`, DESIGN.md / `.env.example` / README Copilot khớp code.
- [x] `python -m unittest discover -s test`: 554 OK, 34 skip · `npx tsc --noEmit` PASS · vitest 93/93 PASS · `check_diff.py` 0 FAIL.
- [ ] Kiểm browser các màn sau đăng nhập (Settings với luồng TOTP, Copilot Lab, LabelStudio, Forecast) ở 375/1024 px × sáng/tối. **NOT RUN:** cần tài khoản test có TOTP.
- [ ] P2 còn mở được sửa hoặc ghi `Deferred` kèm hồ sơ: A-7 (seed ghi đè metrics eval), A-11/12, A-25 (test qua HTTP route), A-37, A-40, A-41, A-53. A-23 chuyển sang [bug-029](../../../bugs/bug-029-db-fallback-tu-tao-database-tren-postgres-khac/bug.md).
- [ ] A-22 (fallback `DOUBLE PRECISION[]` khi không có pgvector): chủ dự án quyết hoặc viết ADR.

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
- Ngoài phạm vi, auditor ghi nhận: `docker-compose.yml:120` bật `AI_CONSOLE_DEMO_SEED_ENABLED=true` ở compose base, trái `DESIGN.md:13`.

## Hồ sơ liên quan

- [AUDIT-006](../../../audits/10-2026/AUDIT-006-console-wip-2026-10-25.md) · [audit-2](review/audit-2.md) · [audit-3](review/audit-3.md)
- [console tools & knowledge](../ISSUE-007-console-tools-and-knowledge-management/issue.md) (đã merge qua PR #71), [ISSUE-008](../ISSUE-008-console-access-policy-regression-tests/issue.md) (test quyền 7 vai)
- IPLMS ADR-0048 (quyền console, step-up), ADR-0051 (accept policy), ADR-0029 (guardrail LLM)
