# 📐 ADR-0003: Agent tranh chấp chỉ đề xuất, người duyệt mới tạo lệnh cho backend

> **Đích:** `docs/projects/adrs/10-2026/0003-nguoi-duyet-truoc-khi-xu-ly-tranh-chap.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Accepted |
| **Ngày** | 2026-10-26 |
| **Người quyết định** | HiTranquility (chọn viết ADR thật cho hồ sơ Final Project, [bug-032](../../bugs/bug-032-ho-so-final-project-lech-voi-repo/bug.md)) |
| **Phạm vi** | IPLMS-AI: `app/core/copilot/engines/dispute_workflow/` |

## Bối cảnh

Workflow tranh chấp (khách khiếu nại phí, mất vé, xe trầy…) dùng LLM để đọc bằng chứng và soạn đề xuất xử lý, có thể dẫn tới hoàn tiền. Đề Final Project §4.1.B yêu cầu hành động thay đổi dữ liệu thật do AI đề xuất phải có người xác nhận. Nội dung khiếu nại do khách viết, có thể chứa câu ra lệnh cho AI (prompt injection).

Hồ sơ nộp bài gọi quyết định này là "ADR-0010" mà không có file; ADR-0010 ở repo gốc là chuyện khác.

## Quyết định

Workflow là một `StateGraph` LangGraph (`graph.py`): `load_evidence → analyze_evidence → retrieve_policy → validate_evidence → draft_recommendation → prepare_human_review → human_review → finalize`.

1. Node `human_review` gọi `interrupt(...)` (`nodes.py`, `request_human_review`): graph dừng, trạng thái lưu ở checkpoint, chờ người duyệt.
2. Payload gửi người duyệt có bằng chứng, đề xuất và `claim_injection_flags` (câu giống lệnh cho AI tìm thấy trong khiếu nại, IPLMS ADR-0029 luật 2).
3. Quyết định duyệt phải qua `validate_review` (hành động hợp lệ, có `reviewer_id`). Chỉ `approve` mới tới `finalize`; `finalize` tự kiểm lại và ném lỗi nếu chưa approve.
4. `finalize` không tự hoàn tiền: nó chỉ tạo `approved_command` (`REVIEW_DISPUTE_RECOMMENDATION`, có `operation_key` idempotent) để backend thực thi.
5. Thiếu bằng chứng thì bỏ qua bước soạn đề xuất, đi thẳng tới người duyệt.

## Các phương án đã cân nhắc

- **A. AI tự duyệt khi độ tin cậy cao.** Nhanh hơn, nhưng độ tin cậy của LLM không phải bảo đảm, và khiếu nại có thể được viết để lừa AI. Trái đề §4.1.B. Không chọn.
- **B. Không dùng LLM, người làm tay từ đầu.** An toàn nhưng mất phần tóm tắt bằng chứng và đối chiếu quy chế, là chỗ AI giúp được nhiều nhất. Không chọn.

## Hệ quả

### Được

- Không có đường nào để LLM tạo lệnh hoàn tiền mà không qua người; kiểm được bằng test không cần model.
- Người duyệt thấy luôn cờ injection, không phải tự đọc để tìm.

### Đánh đổi

- Mỗi tranh chấp tốn thời gian người duyệt; checkpoint phải lưu bền (Postgres) để graph chạy tiếp được sau khi khởi động lại.
- Phụ thuộc package `langgraph`; thiếu thì workflow báo lỗi cấu hình thay vì chạy dở.

## Bằng chứng và liên kết

- Code: `app/core/copilot/engines/dispute_workflow/graph.py`, `nodes.py` (`request_human_review`, `route_after_review`, `finalize`).
- Test: `test/test_dispute_workflow.py` (`test_review_requires_known_action_and_reviewer`, `test_complete_evidence_reaches_draft_and_safe_backend_command`, `test_missing_evidence_skips_recommendation`, `test_llm_overreach_is_rejected`).
- Liên quan: IPLMS ADR-0029 (guardrail LLM).
