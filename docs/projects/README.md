# Projects

Mọi hồ sơ của repo con nằm dưới thư mục này, bố cục giống nhau ở mọi repo con (IPLMS ADR-0054):

```text
docs/projects/
├── BOARD.md                                       # sinh từ Meta hồ sơ (script/board_gen.py), không sửa tay — IPLMS ADR-0060
├── suggestions/MM-YYYY/SUGGESTION-NNN-slug.md    # đề xuất chỉ trong repo này
├── usecases/UC-NNN-slug.md                       # đặc tả cho dev: bảng + sơ đồ sequence/state/ER
├── adrs/MM-YYYY/NNNN-slug.md
├── issues/MM-YYYY/ISSUE-NNN-slug/                # việc triển khai
│   ├── issue.md                                  #   ngoài cùng chỉ file này
│   ├── phase/phase-N.md
│   ├── review/review-N.md · review/audit-N.md    #   review + convention audit
│   ├── handoff/handoff-N.md
│   └── evidence/                                 #   ảnh, log, trace
├── bugs/bug-NNN-slug/                            # bug.md + review/ evidence/ (+ phase/ khi cần)
├── qas/MM-YYYY/QA-NNN-slug.md
├── chores/MM-YYYY/CHORE-NNN-slug/issue.md        # việc không ra tính năng, bố cục như issue
└── audits/MM-YYYY/AUDIT-NNN-slug.md              # quét cả repo theo một quy ước
```

Mỗi thư mục có `README.md`; thư mục con của một hồ sơ (`phase/`, `review/`…) chỉ tạo khi có file đầu. Mẫu ở [`docs/templates/`](../templates/README.md). Việc xuyên repo (IDEA, PROB, ADR hệ thống, REQ) ghi ở repo gốc IPLMS và link hai chiều. Mã số chạy riêng trong repo này — trích sang repo khác thì ghi kèm tên repo, ví dụ `backend UC-003`. Hồ sơ dời từ gốc giữ dòng "Bắt nguồn từ: IPLMS <mã>".
