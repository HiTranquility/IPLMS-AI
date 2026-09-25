# core/knowledge_eval — Bộ test Copilot + cổng xuất bản (ISSUE-009)

> Trạng thái (2026-09-25): code + test xong, E2E gRPC trên container 14/14; **chưa chạy lượt nào với LLM thật** (thiếu `AI_LLM_API_KEY`).

Scope = ID bãi (`parking_lot_id`) hoặc rỗng = tài liệu chung. Quyền theo scope do backend kiểm trước (owner: bãi mình; admin/moderator: chung, đọc bãi; chỉ admin xuất bản chung).

## Luồng

```text
grpc KnowledgeEvalService → app/api/grpc/handlers/knowledge_eval_handler.py → services/eval_service.py

Bộ test      list/upsert/delete_case → infra/database/knowledge_eval_store (knowledge_test_cases)
             kiểm: loại fact | explain | abstain; fact phải có "thông tin bắt buộc"

AI đề xuất   generate_cases: pgvector.latest_version_ids → store.chunks_for_versions (≤40 đoạn)
             → llm_factory.generate_json (Structured Outputs) → engines/case_generator.clean_proposals
             → TRẢ VỀ ĐỀ XUẤT, KHÔNG LƯU (người duyệt rồi upsert)

Chạy test    start_run: bộ test ≤30 câu · có tài liệu · store.create_run (khoá advisory: 1 lượt/scope,
             ≤3 lượt toàn hệ thống) → trả RUNNING ngay → asyncio task nền:
               mỗi câu: copilot rag_pipeline.query(preview=True)
                     → engines/grader.grade (tất định: tiền/giờ chuẩn hoá, nguồn, từ chối)
                     → câu explain qua tất định → engines/judge (LLM-as-judge, rubric cố định)
                     → store.add_result (+ nhịp tim)
               lỗi hạ tầng (thiếu key, DB/LLM) → lượt FAILED + error, KHÔNG tính câu sai
               xong → engines/gate.run_verdict (≥5 câu, ≥90%, 0 sai fact, 0 sai abstain)
                    → PASSED/FAILED; tài liệu không đổi trong lúc chạy → nháp thành TESTED
             nhịp tim quá 180s (replica chết) → đọc ra ABORTED

Xuất bản     readiness: lượt gần nhất PASSED + vân tay (phiên bản mới nhất, bộ test) khớp + còn nháp
             publish: readiness đạt → pgvector.publish_versions (một transaction, bản cũ → ARCHIVED)
             KHÔNG có đường bỏ qua cổng.
```

## File

| File | Việc |
|---|---|
| `services/eval_service.py` | Điều phối tất cả ở trên |
| `engines/grader.py` | Chấm tất định; `normalize`: `25.000 VNĐ`=`25000đ`, `20k`=`20000`, `22h`=`22:00` |
| `engines/judge.py` | Prompt + schema giám khảo AI (chống prompt injection từ tài liệu) |
| `engines/case_generator.py` | Prompt + schema sinh câu hỏi; lọc đề xuất (bỏ nguồn bịa, câu trùng) |
| `engines/gate.py` | Vân tay, ngưỡng lượt chạy, lý do chưa được xuất bản — thuần, không I/O |
| `app/infra/database/knowledge_eval_store.py` | Bảng `knowledge_test_cases/runs/results` |

Cấu hình `AI_EVAL_*` (`app/config/eval_config.py`): `MAX_CASES_PER_RUN=30`, `MAX_CONCURRENT_RUNS=3`, `MAX_GENERATED_CASES=20`, `MIN_CASES=5`, `MIN_PASS_RATIO=0.9`, `STALE_AFTER_SECONDS=180`, `JUDGE_MODEL`, `JUDGE_ENABLED`. Test: `test/test_knowledge_eval.py`.

Giao diện: operator tab "Quy Chế Cho AI Copilot" và platform "Kho tri thức AI" dùng chung `KnowledgeBaseWorkbench` (`frontend/packages/shared`).
