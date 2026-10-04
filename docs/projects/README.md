# Projects

Mọi hồ sơ của repo con nằm dưới thư mục này, để bố cục giống nhau ở mọi repo con:

```text
docs/projects/
├── BOARD.md                                      # ai nhận việc gì, hạn, tới đâu — một dòng mỗi việc
├── suggestions/MM-YYYY/SUGGESTION-NNN-slug.md   # đề xuất chỉ trong repo này
├── usecases/UC-NNN-slug.md                      # đặc tả cho dev: bảng + sơ đồ sequence/state/ER
├── adrs/NNNN-slug.md
├── issues/MM-YYYY/ISSUE-NNN-slug/issue.md
├── bugs/bug-NNN-slug/bug.md
└── qas/MM-YYYY/QA-NNN-slug.md
```

Thư mục con chỉ tạo khi có hồ sơ đầu tiên. Việc xuyên repo (IDEA, PROB, ADR hệ thống, REQ) ghi ở repo gốc và link hai chiều. Mã số chạy riêng trong repo này — trích sang repo khác thì ghi kèm tên repo, ví dụ `backend UC-003`.
