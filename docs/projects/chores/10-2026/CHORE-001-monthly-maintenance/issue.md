# 🧹 CHORE-001: Việc vặt tháng 10/2026

> **Đích:** `docs/projects/chores/10-2026/CHORE-001-monthly-maintenance/issue.md` — nhánh `chore/CHORE-001-2026-10-monthly-maintenance`, một PR vào `develop` cuối tháng (IPLMS ADR-0055)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ngày tạo** | 2026-10-21 |
| **Người phụ trách** | @HiTranquility |
| **Phạm vi** | Việc vặt tháng 10/2026 của repo này |

## Việc đã gom

| # | Việc | Nguồn | Commit |
|---|---|---|---|
| 1 | Luật "ý tưởng giữa chừng": dòng trong `AGENTS.md` + ô **Techlead duyệt** / **Làm trước khi duyệt?** trong mẫu SUGGESTION | IPLMS ADR-0059, IPLMS REQ-017 | (commit đầu nhánh) |
| 2 | Đổi số trích dẫn: IPLMS ADR-0056/REQ-014 → ADR-0059/REQ-017 (gốc trùng số với develop) | IPLMS bug-054 | (commit này) |
| 3 | BOARD: chuyển bug-015…026 và SUGGESTION-003 (đã merge #50–#55) từ 🙋 xuống ✅, theo `check_drift.py` của gốc | ai ISSUE-004 review-2 | (commit nhánh `chore/CHORE-001-2026-10-board-sweep`) |
| 4 | Xác nhận mục 3b `AI_USAGE.md` phần Chủ M2 (Telemetry Copilot `ai_request_log_store.py`, `usage_service.py`) và cập nhật `BOARD.md` tiến độ của Dương (@23110012) | IPLMS ISSUE-126 phase-6 6.6 | (commit này) |
| 5 | Viết lại `README.md` (chạy, biến môi trường không giá trị, tài khoản test, đối chiếu đề Final Project) và `ui/README.md` (màn hình hiện tại, cấu trúc `src/`); thêm README cho `app/`, `test/`, `data/`, `docker/`, `script/`. Lỗ hổng so với đề ghi ở bug-032 | `docs/references/final-project-assignment-guidelines.md` §9 | (commit này) |

## Tiêu chí chấp nhận

- [ ] Mỗi việc ở bảng trên có commit và đã kiểm (docs: link không gãy).
- [ ] Một PR vào `develop` liệt kê đủ các dòng trên.
