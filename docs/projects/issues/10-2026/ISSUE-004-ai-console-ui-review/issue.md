# 🏷️ ISSUE-004: Rà AI Console `ai/ui` bằng REA: bug, UI/UX, độ khớp quy chuẩn, đề xuất và giao việc

> **Đích:** `docs/projects/issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Done (chỉ ghi hồ sơ; không sửa code) |
| **Người nhận** | Claude Code |
| **Người phụ trách** | Claude Code, theo yêu cầu chủ dự án ngày 2026-10-23 |
| **Phạm vi** | `ai/ui`, cùng phần API console mà UI gọi (`app/api/rest/routes/console_*`, `app/console_main.py`) |
| **Nhánh** | `docs/ISSUE-004-2026-10-ai-console-ui-review` |

Bắt nguồn từ: IPLMS ISSUE-126 (AI Console nội bộ), [ISSUE-003](../ISSUE-003-console-root-routing-copilot-studio/issue.md) (Chat Studio và các studio mô phỏng).

## Mục tiêu

Nguyên văn yêu cầu của chủ dự án:

> "với cái REA mới, bạn thử chạy và coi cái ai/ui nha, coi có thể vừa coi bug nè, rồi tính năng nên đề xuất là gì, những tính năng hiện tại UI/UX ra sao, có ổn không? Từ code đến quy trình chuẩn chưa, nên thêm bớt gì, chỉ cần ghi ý tưởng bug vào thôi, tui sẽ để bên khác làm. Miễn là đúng chuẩn kỹ, sau đó thấy với những việc đó, Phat, Duong Khoa nên được giao thêm gì? (Phần UI/UX hay này kia Phat làm hết) rồi xong đóng commit lại là đc"

## Tiêu chí chấp nhận

- [x] Chạy `ai/ui` và xem bằng REA (`inspect_web_page`, `capture_web_screenshot`) cùng browser: 11 màn hình, xem [review-1](review/review-1.md) §Đã kiểm thế nào.
- [x] Mỗi bug có bằng chứng được ghi thành một hồ sơ: [bug-015](../../../bugs/bug-015-dev-session-cua-hau-dang-nhap/bug.md) … [bug-023](../../../bugs/bug-023-che-do-en-tron-tieng-viet/bug.md) (9 bug), cùng 2 bug của lượt bổ sung: [bug-024](../../../bugs/bug-024-trang-cong-cu-tran-ngang-o-768px/bug.md), [bug-025](../../../bugs/bug-025-mau-chu-faded-va-accent-duoi-nguong-tuong-phan/bug.md).
- [x] Lượt bổ sung 2026-10-24: chạy các mục còn NOT RUN (theme sáng, 768px, parse mermaid). Ảnh trong [evidence/v2/](evidence/v2/), kết quả trong [review-1](review/review-1.md) §Đã kiểm thế nào. Đăng nhập thật và DB thật vẫn BLOCKED.
- [x] Có đánh giá UI/UX từng tính năng, độ khớp với AI_CONVENTIONS, `ui/DESIGN.md` và quality-gate L1–L8, cùng các mục nên thêm hoặc bớt: [review-1](review/review-1.md).
- [x] Ý tưởng tính năng được ghi: [SUGGESTION-001](../../../suggestions/10-2026/SUGGESTION-001-dang-nhap-dev-cuc-bo-an-toan.md) … [SUGGESTION-005](../../../suggestions/10-2026/SUGGESTION-005-gom-luot-chat-vao-bo-eval.md).
- [x] Có đề xuất giao việc cho Phát, Dương và Khoa (toàn bộ UI/UX giao Phát), ghi trong [BOARD](../../../BOARD.md) mục 🙋 và review-1 §Giao việc.
- [x] Không sửa code ứng dụng: commit chỉ có file trong `docs/`.

## Kế hoạch

1. Dựng UI dev (`vite`, cổng 5190) và API giả (`evidence/mock_console_api.py`, cổng 8090) → kiểm: `/console/api/me` trả 401 hoặc 200 theo chế độ.
2. Mở Chrome headless có CDP, nối với REA trong WSL bằng đường hầm ngược → kiểm: `inspect_web_page` đọc được cây a11y.
3. Chụp và đọc code từng màn → kiểm: mỗi bug có `file:line`.
4. Ghi hồ sơ, BOARD, commit và push nhánh.

## Hồ sơ liên quan

- Bug: bug-015 … bug-026 · Sửa: [review-2](review/review-2.md) · Suggestion: SUGGESTION-001 … 005 · Báo cáo: [review-1](review/review-1.md) · Ảnh: [evidence/](evidence/)
- [AUDIT-005](../../../audits/10-2026/AUDIT-005-ai-console-security-review.md): cần đính chính vì không nêu bug-015 và bug-016.
