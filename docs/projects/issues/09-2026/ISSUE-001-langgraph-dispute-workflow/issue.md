# 🏷️ ISSUE-001: [Feature] LangGraph Workflow Cho Copilot Tranh Chấp

> **Đích:** `docs/projects/issues/09-2026/ISSUE-001-langgraph-dispute-workflow/` · **Luật chung:** [templates/README](../../../../templates/README.md)

## 🎯 Goal (Mục tiêu)

Tạo lát cắt LangGraph đầu tiên cho dispute: state có schema, node thuần có dependency injection, pause/resume để nhân viên duyệt, checkpoint memory cho test và PostgreSQL adapter cho production. Workflow chỉ trả đề xuất đã duyệt cho backend; không tự hoàn tiền hoặc sửa session.

## 📌 Meta

| | |
|---|---|
| **ID** | ISSUE-001 |
| **Bắt nguồn từ** | IPLMS ISSUE-005 (`docs/projects/issues/09-2026/ISSUE-005-langgraph-dispute-workflow`), dời về ai ngày 2026-10-18 theo ADR-0054 |
| **Người viết** | Codex + chủ đồ án |
| **Trạng thái** | 🚧 In Progress (phase 2 complete) |
| **Người nhận** | Dương |
| **Hạn** | 2026-10-18 |
| **Danh mục** | `ai` |
| **Depends On** | PROB-035 direct RAG; object refs trong parking session |
| **Used By** | Copilot dispute review/API ở phase sau |
| **Architecture** | Direct RAG giữ nguyên; bounded LangGraph workflow + checkpointer adapter |
| **Link liên quan** | [PROB-040](../../../../../../docs/problems/09-2026/PROB-040-langgraph-copilot-stateful-workflow.md) |
| **Breaking change?** | Không — graph chưa thay contract gRPC hiện tại |

## 💻 Stack & Impact

| Component | Details |
|---|---|
| **AI runtime** | Python 3.10+, LangGraph, typed state, async nodes |
| **Persistence** | In-memory cho test; PostgreSQL checkpointer cho production |
| **Impact** | Thêm workflow read-only; Q&A RAG và `ArbitrateDispute` hiện tại không đổi |

## 🔴 Problems / Current State Issues

1. `ArbitrateDispute` chưa có evidence workflow, checkpoint hoặc human review.
2. Direct RAG phù hợp Q&A nhưng không quản lý được pause/resume nhiều bước.
3. Chưa có ranh giới code ngăn model tự thực thi hành động tài chính.

## ✅ Tasks Breakdown

### Phase 1 — Bounded graph foundation

- [x] State/version/status và dependency protocols.
- [x] Graph nodes: load evidence, analyze, retrieve policy, validate, draft, review, finalize.
- [x] Human-review interrupt và resume validation.
- [x] Memory/PostgreSQL checkpointer factory.
- [x] Config/dependency manifest và unit/integration tests.

### Phase sau

- [x] PostgreSQL schema isolation, setup/check CLI và retention dry-run/apply (`148e101`).
- [x] Bổ sung contract evidence fixture (`fixtures.py`) và bộ mock adapters cho caller backend.
- [x] Bổ sung test hồi quy restart/resume qua checkpoint, thread sai, duyệt lặp idempotent, duyệt sai.
- [x] Nối engine LangGraph thật vào route `/copilot/dispute-workflow/simulate` thay thế bước giả lập.
- [ ] Backend evidence bundle có authorization (bàn giao caller cho HiTranquility).
- [ ] API/UI review và audit.
- [ ] Backend idempotent approved-action handler.
- [ ] Outbox/RabbitMQ trigger khi có nhu cầu scale.

## 🛠️ Technical Details / Architecture

```text
backend authorized evidence bundle
  → load → analyze Vision → retrieve policy → validate
  → draft recommendation → interrupt(human review)
  → approved_for_backend | rejected
```

## ↩️ Rollback Plan

Revert commit AI và submodule pointer. Phase 1 không tạo migration nghiệp vụ, không thay proto và không ghi action tài chính. Bảng checkpoint chỉ được tạo khi production setup được gọi rõ ràng.

## 🚫 Non-goals

- Không thay direct Q&A RAG bằng LangChain.
- Không mở lại endpoint arbitration hiện tại.
- Không xây payment/refund action, UI review, outbox hoặc RabbitMQ trong phase 1.
- Không gửi trace sang LangSmith trong phase 1.

## 🔐 Security gate

- **Chạm tiền / thao tác không được lặp?** Chưa chạm tiền; output cuối chỉ là `approved_for_backend` và có operation key.
- **Thêm/hiển thị/log dữ liệu cá nhân (PII)?** State chỉ nhận evidence đã scope; không log prompt, biển số, URL hoặc bytes ảnh.
- **Có input mới từ client / thêm endpoint?** Không trong phase 1.
- **Đổi quyền / ranh giới truy cập?** Không; graph không có raw SQL/payment tool.
- **Guardrail LLM ([ADR-0029](../../../../../../docs/projects/adrs/10-2026/0029-nguyen-tac-guardrail-llm.md), [PROB-046](../../../../../../docs/problems/10-2026/PROB-046-guardrail-prompt-injection-cho-llm.md) phase 4):** đề xuất của writer qua `validate_recommendation` (enum, số tiền ≤ min(số tiền đòi, phí phiên), nguồn đã truy xuất); `claim_reason` ≤ 2000 ký tự và được quét lệnh cho AI. Viết writer LLM thật thì phải chạy red-team riêng cho luồng này.

## 📊 Acceptance Criteria

- [x] Happy path dừng ở interrupt và resume thành `approved_for_backend`.
- [x] Reject kết thúc mà không gọi finalizer.
- [x] Thiếu evidence vẫn vào human review với cảnh báo rõ.
- [x] State không chứa bytes ảnh, signed URL dài hạn, access token hoặc chain-of-thought.
- [x] PostgreSQL checkpointer là adapter opt-in; memory saver dùng cho test.
- [x] Direct Q&A tests tiếp tục pass; `ArbitrateDispute` vẫn fail closed.
- [x] Full AI test suite và compileall pass.

## 🧪 Verification

| Kiểm tra | Kết quả |
|---|---|
| `pip check` | Không có dependency lỗi |
| `python -m unittest test.test_dispute_workflow` | 19 pass, 0 skip, 0 fail |
| `python -m compileall -q app test` | Pass |
| Dependency security floor | `langgraph-checkpoint 4.3.0`, `langgraph-sdk 0.4.9` |
| Phase 1 AI commit | `83e34d0` |

Phase 2: [PostgreSQL checkpoint operations](phase/phase-2.md), AI commit `148e101`.
Phase 3: Test restart/resume, thread sai, duyệt lặp, contract evidence fixture và REST simulation wiring.
