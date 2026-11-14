# 🧹 CHORE-002: Việc vặt tháng 11/2026

> **Đích:** `docs/projects/chores/11-2026/CHORE-002-monthly-maintenance/issue.md` — nhánh `chore/CHORE-002-2026-11-monthly-maintenance`, một PR vào `develop` (IPLMS ADR-0066)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-11-30 |
| **Ngày tạo** | 2026-11-03 |
| **Người phụ trách** | @HiTranquility |
| **Phạm vi** | Chuẩn hoá cấu trúc `app/core`, tên file/mã ISSUE trùng, `README.md` ≤ 120 dòng và đồng bộ templates/UC tháng 11/2026 |

## Việc đã gom

| # | Việc | Nguồn | Commit |
|---|---|---|---|
| 1 | Chuẩn hoá `check_core_layout.py` về 0 lệch: thêm `ConsoleAuthService.validate_permission` để `console_access.py` không import trực tiếp `engines`; dời `EvaluationSample` sang `app/core/dataset/dtos/sample_dto.py` và tái xuất qua `app.core.dataset` (lazy load PEP 562 tránh nạp `cv2` sớm) | IPLMS ISSUE-128 | (commit này) |
| 2 | Chuẩn hoá `check_naming.py` về 0 lỗi/0 cảnh báo: `clean_history.sh` → `clean-history.sh`; tách mã trùng `ISSUE-007` → `ISSUE-027`, `ISSUE-020` → `ISSUE-028`; dời `schema-chang-2-connections.md` vào `ISSUE-022/phase/`; đóng `ISSUE-024` đã merge PR #118; rút gọn `README.md` còn 92 dòng | IPLMS REQ-001, REQ-011 | (commit này) |
| 3 | Đồng bộ `docs/templates/usecase-template.md`, thêm `script/usecase_index.py` và khung tự sinh `docs/projects/usecases/README.md` (ADR-0065) | IPLMS ADR-0065 | (commit này) |
| 4 | Bỏ luật copy/symlink `.env*` sang worktree trong `AGENTS.md` + `CLAUDE.md` (trái STRICT PRIVACY), thay bằng mục Worktree ngắn trỏ IPLMS ADR-0070 §2 (IPLMS REQ-031 F5) | [IPLMS ADR-0070](https://github.com/HiTranquility/IPLMS/blob/develop/docs/projects/adrs/11-2026/0070-mot-nguon-luat-agent-worktree-khong-env-gitlink-va-dong-bang-quy-trinh.md) | (commit này) |

## Tiêu chí chấp nhận

- [x] `python -X utf8 script/check_core_layout.py --core app/core` đạt 0 lệch.
- [x] `python -X utf8 script/usecase_index.py --check` và `python -X utf8 script/check_generated.py` đạt 0 lỗi.
- [x] `python -X utf8 script/check_branch_policy.py --branch chore/CHORE-002-2026-11-monthly-maintenance` đạt.