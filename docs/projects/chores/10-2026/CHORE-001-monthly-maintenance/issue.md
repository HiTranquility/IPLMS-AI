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
| 6 | Audit một lượt phần vào develop ngày 27/10 ([AUDIT-007](../../../audits/10-2026/AUDIT-007-develop-2026-10-27-console-knowledge-settings.md)) và mở hồ sơ [bug-039](../../../bugs/bug-039-trang-knowledge-mau-ghi-cung-vo-tuong-phan-theme-sang/bug.md), [bug-040](../../../bugs/bug-040-history-copilot-khong-qua-rao-chan-dau-vao/bug.md). Chỉ ghi hồ sơ, việc sửa đi nhánh bugfix riêng | AUDIT-007 | (commit này) |
| 7 | Audit lối vào inference ([AUDIT-008](../../../audits/10-2026/AUDIT-008-loi-vao-inference-rate-limit-upload-cors-grpc.md)): rate-limit, upload ảnh ANPR, CORS, gRPC. Mở [bug-043](../../../bugs/bug-043-anpr-rest-doc-anh-khong-gioi-han-kich-thuoc/bug.md), [bug-044](../../../bugs/bug-044-anpr-recognize-many-khong-gioi-han-so-file/bug.md), [bug-045](../../../bugs/bug-045-cors-inference-phan-chieu-moi-origin-kem-credentials/bug.md), [bug-046](../../../bugs/bug-046-loi-vao-ai-khong-gioi-han-toc-do-va-dong-thoi/bug.md); phần backend là backend bug-019. Chỉ ghi hồ sơ, việc sửa đi nhánh bugfix riêng | Câu hỏi @HiTranquility 2026-10-27 | (commit này) |
| 8 | Chuẩn bị nộp báo cáo: `.env.example` đủ mọi biến code/compose đọc (thêm nhóm Docker Compose + tuỳ chọn nâng cao dạng comment kèm mặc định); `README.md` thêm mục "Thử nhanh luồng AI" (lệnh curl + 3 guardrail + kết quả kiểm 2026-10-31) và nhóm biến Compose. Test luồng AI mở [bug-051](../../../bugs/bug-051-guard-ngoai-pham-vi-khong-chuan-hoa-unicode-va-de-lach-bang-dien-dat-lai/bug.md) (guard ngoài phạm vi lọt với NFD/diễn đạt lại) và [bug-052](../../../bugs/bug-052-copilot-bao-khong-co-thong-tin-khi-llm-hoac-embedding-sap/bug.md) (AI sập báo nhầm "không có thông tin"). Kiểm: env drift 0 thiếu, `docker compose config` với `.env.example` OK, unit 706 OK, eval 27/27 | Chủ dự án 2026-10-31 (đề Final §9) | (commit này) |
| 9 | Báo cáo Final Project bản Word vào `docs/references/Final_Projects_Report_IPLMS-AI.docx` (README trỏ tới). Đối chiếu với code `develop`: Python 3.11 trong image (CI 3.13), 76 module test, prompt ở `data/prompts/copilot_rag_system/v2.md` + `app/infra/llm/prompts.py` (ADR-0005, hash `e88e1965` khớp), `engines/anpr/engine.py`, kiểm tên nhánh bằng CI BranchPolicy; thêm link repo (bìa, §4.1), lệnh chạy Docker Compose từ clone riêng (ADR-0006), hai dòng bảng 5.5 (triển khai, secret/bug-053) | Chủ dự án 2026-10-31 (đề Final §9) | (commit này) |
| 9 | bug-049 ghi lượt đo với Ollama thật (`qwen2.5:3b`, `develop` `e07413a`): `redteam_copilot -n 5` 0 chặn nhầm 15/15, tấn công 0/20 lọt; `redteam_agent` 60 biến thể 0 lọt — điều kiện audit A-3 đã đạt; A-5 chưa đo lại | [bug-049](../../../bugs/bug-049-guard-copilot-khong-chuan-hoa-unicode-truoc-khi-so-regex/bug.md), IPLMS REQ-024 | (commit này) |

## Tiêu chí chấp nhận

- [ ] Mỗi việc ở bảng trên có commit và đã kiểm (docs: link không gãy).
- [ ] Một PR vào `develop` liệt kê đủ các dòng trên.
