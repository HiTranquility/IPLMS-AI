# 🐛 bug-012: Test `publish_scope` dùng fixture `validate` cũ, luôn FAIL khi có Postgres thật

> **Đích:** `docs/projects/bugs/bug-012-test-publish-concurrency-fixture-cu/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-17 / Claude Code |
| **Trạng thái / Mức độ** | ✅ Fixed — chờ PR / P3 (chỉ test, không đổi code chạy) |
| **Nguồn** | IPLMS ISSUE-126 phase-6 (đo baseline với Postgres 16 + pgvector tạm) |

`test/test_publish_concurrency.py` truyền cho `KnowledgeEvalStore.publish_scope` một hàm `validate` 6 tham số. Từ `a50aa21` (PROB-046 phase 2) store gọi `validate(..., active_profile_ids, flagged)` — 7 tham số — nên trong transaction nổ `TypeError`, bị `_tx` gói thành `RagPipelineError("Truy vấn bộ test Knowledge Base thất bại.")`. Test chờ `KnowledgeGateError` nên FAIL.

Test chỉ chạy khi có `AI_TEST_DATABASE_URL` trỏ Postgres có pgvector; CI và máy thiếu DB bỏ qua nó, nên lỗi không ai thấy. Code chạy thật không sai: chỉ fixture trong test lệch chữ ký.

**Tái hiện:** `AI_TEST_DATABASE_URL=postgresql://…/postgres python -m unittest test.test_publish_concurrency` trên `develop@b99f698` → `FAILED (failures=1)`; nguyên nhân gốc lấy ra bằng cách in `__cause__`: `validate() takes 6 positional arguments but 7 were given`.

**Sửa:** thêm tham số `flagged` vào fixture. Sau sửa: `Ran 1 test … OK` trên cùng DB.

**Rủi ro còn lại:** các test cần DB thật không chạy trong CI → lệch chữ ký kiểu này sẽ lặp lại. Gợi ý (chưa làm): thêm service Postgres + pgvector vào job CI Python.
