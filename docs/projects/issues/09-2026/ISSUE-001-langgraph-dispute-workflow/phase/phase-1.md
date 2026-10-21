# 🚀 [Phase 1] Bounded Graph Foundation Và Human Review

> **Đích:** `docs/projects/issues/09-2026/ISSUE-001-langgraph-dispute-workflow/phase/` · **Luật chung:** [templates/README](../../../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **Thuộc Issue** | [ISSUE-001](../issue.md) |
| **Người thực hiện** | Codex |
| **Ngày bắt đầu** | 2026-09-21 |
| **Trạng thái** | Complete |

## 🎯 Mục tiêu Phase

Tạo graph read-only có thể test độc lập, dừng chờ review và resume an toàn. Tách phase này khỏi backend evidence/action contract để không mở quyền tài chính khi orchestration chưa được kiểm chứng.

## 🔗 Phụ thuộc

- **Blockers:** Không; node dùng protocol và fake dependency trong test.
- **Blocks:** Evidence API, review UI/API, PostgreSQL integration test và approved action.

## ✅ Danh sách Task trong Phase

- [x] Typed state, dependency protocols và validation thuần.
- [x] LangGraph builder với conditional routes và interrupt.
- [x] Checkpointer factory memory/PostgreSQL.
- [x] Config + requirements ở cả dev/service.
- [x] Test happy path, reject, missing evidence, invalid review và config.

## 🛠 Chi tiết triển khai

```text
ai/app/core/copilot/engines/dispute_workflow/
├── state.py
├── dependencies.py
├── nodes.py
└── graph.py

ai/app/infra/workflow/
└── checkpointer.py
```

Graph không được import vào singleton `CopilotService` trong phase này; `ArbitrateDispute` tiếp tục `UNIMPLEMENTED`.

## 🧪 Kế hoạch Kiểm thử

**📸 Baseline TRƯỚC khi làm:**

| Lệnh | Kết quả trước phase |
|---|---|
| `.venv/Scripts/python -m unittest discover -s test -t .` | 137 pass / 0 fail / 2 skip |
| `python -m compileall -q app test` | sẽ đo cùng verification cuối phase |

- [x] Unit test node/state không cần network/database.
- [x] Integration test graph bằng `InMemorySaver` sau khi dependency được duyệt/cài.
- [x] Full suite không giảm số test pass: 151 pass, 2 skip, 0 fail.

## ✅ Definition of Done

- [x] Test/compileall pass và direct RAG không đổi contract.
- [x] Commit AI `83e34d0`, không lẫn thay đổi đang làm dở.
- [x] Issue/phase cập nhật với bằng chứng và giới hạn chưa làm.

## 📦 Dependency đã resolve

| Package | Version |
|---|---:|
| `langgraph` | `1.2.11` |
| `langgraph-checkpoint` | `4.2.0` |
| `langgraph-checkpoint-postgres` | `3.1.2` |
| `langgraph-sdk` (gián tiếp) | `0.4.4` |
| `psycopg` | `3.3.6` |

`pip check` không phát hiện dependency hỏng. LangSmith được kéo gián tiếp bởi `langchain-core`, nhưng workflow không cấu hình tracing hay gửi dữ liệu ra ngoài.

## ⚠️ Notes / Open Questions

- PostgreSQL saver cần integration test với DB thật ở phase sau.
- Backend evidence bundle và review endpoint chưa có contract; không được giả lập thành production API.
