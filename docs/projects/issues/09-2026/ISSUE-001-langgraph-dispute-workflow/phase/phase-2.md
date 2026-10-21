# 🚀 [Phase 2] PostgreSQL Checkpoint Operations

> **Đích:** `docs/projects/issues/09-2026/ISSUE-001-langgraph-dispute-workflow/phase/` · **Luật chung:** [templates/README](../../../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **Thuộc Issue** | [ISSUE-001](../issue.md) |
| **Người thực hiện** | Codex |
| **Ngày bắt đầu** | 2026-09-21 |
| **Trạng thái** | Done |

## 🎯 Mục tiêu Phase

Đưa PostgreSQL checkpointer từ adapter có thể import thành thành phần vận hành được: schema riêng, setup chủ động, readiness không lộ DSN và retention có dry-run mặc định.

**Vì sao tách phase:** DDL và xóa checkpoint có rủi ro vận hành khác với logic graph. Phase này không nối evidence API, không mở endpoint dispute và không đụng action tài chính.

## 🔗 Phụ thuộc

- **Blockers:** Phase 1 (`83e34d0`) đã hoàn thành graph và checkpointer factory.
- **Blocks:** Restart integration test, evidence API và production rollout.

## ✅ Danh sách Task trong Phase

- [x] Cô lập bảng checkpoint trong PostgreSQL schema được validate.
- [x] CLI setup/check/prune; prune mặc định dry-run và có batch limit.
- [x] Readiness report không in credential hoặc checkpoint payload.
- [x] Unit test cho DSN/search path, schema validation và retention selection.
- [x] Integration test thật bằng PostgreSQL local với schema tạm.

## 🛠 Chi tiết triển khai

```text
AI_WORKFLOW_CHECKPOINT_DATABASE_URL
  → validate schema name
  → setup: CREATE SCHEMA + LangGraph migrations
  → check: tables + migration version
  → prune: tìm thread quá retention → dry-run | delete bounded batch
```

Runtime service không tự chạy DDL mặc định. Role vận hành chạy setup một lần; role runtime chỉ cần quyền trên schema checkpoint.

```bash
python -m app.script.manage_workflow_checkpoints setup
python -m app.script.manage_workflow_checkpoints check
python -m app.script.manage_workflow_checkpoints prune --retention-days 30
python -m app.script.manage_workflow_checkpoints prune --retention-days 30 --apply
```

`prune` không có `--apply` chỉ báo số thread khớp và khoảng thời gian, không in raw thread ID. Trên Windows, CLI chủ động dùng `SelectorEventLoop` tương thích Psycopg async.

## 🧪 Kế hoạch Kiểm thử

**📸 Baseline TRƯỚC khi làm:**

| Lệnh | Kết quả trước phase |
|---|---|
| `.venv/Scripts/python -m unittest discover -s test -t .` | 151 pass / 0 fail / 2 skip |
| `.venv/Scripts/python -m compileall -q app test` | Pass |
| `pip check` | Không có dependency lỗi |

- [x] Unit test không cần network/database: 8 test mới pass.
- [x] CLI help và fail-fast khi thiếu URL.
- [x] Full suite: 166 pass / 0 fail / 2 skip; compileall và `pip check` pass.

**Live PostgreSQL verification:**

| Kịch bản | Kết quả |
|---|---|
| Setup schema + LangGraph migration | Ready, migration version 9 |
| Pause → đóng checkpointer → mở lại → resume | `awaiting_review` → `approved_for_backend` |
| Retention dry-run | Match 1, delete 0 |
| Retention `--apply` | Delete 1, còn 0 thread |
| Cleanup | 0 schema test còn lại |

## ✅ Definition of Done

- [x] Setup/check/prune có JSON output và không lộ secret.
- [x] Không xóa dữ liệu nếu thiếu cờ `--apply` rõ ràng.
- [x] Test và compileall pass.
- [x] AI commit `148e101`; root pointer/docs commit riêng.

## ⚠️ Notes / Open Questions

- Live test dùng credential local sẵn có trong `backend/.env`; không in DSN/password và không dùng database remote.
- Retention chỉ xóa workflow thread quá hạn, không thay thế audit record nghiệp vụ ở backend.
- Production credential/role/grant chưa được kiểm thử; endpoint dispute vẫn fail closed.
