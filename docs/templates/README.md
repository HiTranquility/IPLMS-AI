# Bộ mẫu tài liệu của repo con

Bộ mẫu tối thiểu cho người làm trực tiếp trong repo này. Repo gốc giữ toàn bộ danh mục hồ sơ xuyên hệ thống (IDEA, PROB, REQ, ADR hệ thống…); chọn mẫu nhỏ nhất vừa với việc, và link hai chiều sang hồ sơ ở repo gốc khi thay đổi vượt ranh giới repo.

| Tình huống | Mẫu | Đích |
|---|---|---|
| Đề xuất cải tiến chỉ trong repo này | [suggestion](suggestion-template.md) | `docs/projects/suggestions/MM-YYYY/SUGGESTION-NNN-slug.md` |
| Đặc tả cho dev một hành vi (bảng + sơ đồ sequence bắt buộc) | [usecase](usecase-template.md) | `docs/projects/usecases/UC-NNN-slug.md` |
| Quyết định kỹ thuật chỉ ảnh hưởng repo này | [adr](adr-template.md) | `docs/projects/adrs/NNNN-slug.md` |
| Việc triển khai | [issue](issue-template.md) | `docs/projects/issues/MM-YYYY/ISSUE-NNN-slug/issue.md` |
| Lỗi | [bug](bug-template.md) | `docs/projects/bugs/bug-NNN-slug/bug.md` |
| Câu hỏi kỹ thuật | [qa](qa-template.md) | `docs/projects/qas/MM-YYYY/QA-NNN-slug.md` |
| Giao việc, xem ai đang nhận gì (bug/tính năng chưa làm) — một dòng mỗi việc, trỏ tới hồ sơ | [board](board-template.md) | `docs/projects/BOARD.md` *(một file, không mã, không theo tháng)* |

- Mọi hồ sơ nằm dưới `docs/projects/`; thư mục con chỉ tạo khi có hồ sơ đầu tiên.
- Mã số chạy riêng trong repo này. Trích sang repo khác thì ghi kèm tên repo, ví dụ `backend UC-003`.
- `usecase-template.md` giống hệt bản ở repo gốc: sửa ở repo gốc rồi chép lại.
