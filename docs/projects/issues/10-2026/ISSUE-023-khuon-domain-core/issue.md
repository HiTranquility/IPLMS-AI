# 🏷️ ISSUE-023: Đưa `app/core/` về khuôn domain của ADR-0005 (prompt ra `data/prompts/`, slot tuỳ chọn có tên cố định)

> **Đích:** `docs/projects/issues/10-2026/ISSUE-023-khuon-domain-core/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress — code đã merge, còn chạy `redteam_copilot.py` khi có LLM local |
| **Người nhận** | @HiTranquility |
| **Hạn** |  |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** |  |
| **Người phụ trách** | HiTranquility |
| **Phạm vi** | IPLMS-AI: `app/core/**`, `app/infra/llm/`, `data/prompts/`, `test/`, `app/script/`, `script/`, `benchmark/`, `training/` |

## Mục tiêu

Mọi domain trong `app/core/` theo đúng khuôn ở [ADR-0005](../../../adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md): ba thư mục lõi, chỉ dùng slot tuỳ chọn có tên trong danh sách, text gửi LLM nằm ở `data/prompts/`, không còn bản chép trùng. Đây là refactor: **hành vi ra ngoài không đổi** (proto, REST, câu trả lời, nhãn `promptVersion`).

## Tiêu chí chấp nhận

- [x] `script/check_core_layout.py` báo 0 lệch, có test (`script/test_check_core_layout.py`), chạy trong CI (`.github/workflows/ci.yml`, bước "Check core layout"). CI GitHub hiện không chạy vì lỗi thanh toán tài khoản, nên mới kiểm ở máy.
- [x] `data/prompts/` có `copilot_rag_system/`, `eval_judge/`, `eval_generator/`; `prompt_store` cho version + hash; không còn `DEFAULT_FALLBACK_PROMPT`, thiếu file thì báo lỗi (`test/test_prompt_store.py`). Telemetry Copilot ghi nhãn. Lượt chạy eval chưa ghi nhãn prompt judge/generator vào kết quả.
- [x] `llm_factory.py` dựng user message từ một khuôn `_user_message` đọc `data/prompts/copilot_rag_system/user.md`.
- [x] `NO_CONTEXT_ANSWER`, `GUARD_NOTICE` khai một lần ở `copilot/messages.py`. Marker từ chối ở lại `grader.py` (lý do ở ADR-0005 mục 4); `test_knowledge_eval.py::test_marker_khop_cau_tu_choi_cua_copilot` đỏ khi đổi câu mà quên marker. `eval_copilot_e2e.py` giữ heuristic rộng riêng (chỉ đánh dấu để kiểm tay).
- [x] Nhãn `promptVersion` giữ `copilot_rag_system_v2#e88e1965` (hash không đổi vì nội dung giữ nguyên); `test_rag_pipeline.py::test_system_prompt_loaded_from_versioned_file` kiểm dạng nhãn.
- [ ] `python -m unittest discover -s test -t .` sau mỗi chặng: 603 test, đỏ đúng 2 test có sẵn của bug-047 (giống `develop`), skip 36. **`redteam_copilot.py` chưa chạy** (Ollama không chạy trên máy). Prompt giữ nguyên từng byte, guard chỉ đổi chỗ.
- [x] AI_CONVENTIONS §2 khớp code, `verified-against-code` 2026-10-28.

## Kế hoạch và kết quả

| Chặng | Commit | Việc |
|---|---|---|
| 0 | `ea83738` | bug-042 merge (PR #112); rebase nhánh lên `develop` |
| 1 | `0ec3208` | `script/check_core_layout.py` + test |
| 2 | `615260c` | copilot: `infra/llm/prompts.py`, `data/prompts/copilot_rag_system/{v2,user}.md`, `messages.py`, `guardrails/` (output_guard, pii_redactor), `workflows/dispute/`, một khuôn user message |
| 3 | `57d670d` | knowledge: `guardrails/injection_scan.py`; knowledge_eval: prompt + schema + khuôn input ra `data/prompts/eval_judge/`, `eval_generator/`; test hợp đồng marker |
| 4 | `fd80a73` | vision: `engines/anpr/{engine,onnx_engine,two_line_plate_parser}.py`; `vision/constants.py` |
| 5 | `ace0521` | forecast: `readers/` → `engines/`; hằng một domain → `forecast/constants.py`, `knowledge/constants.py` |
| 6 | (commit này) | CI chạy script kiểm; cập nhật ADR-0005, AI_CONVENTIONS, báo cáo [review-1](review/review-1.md) |

### Lệch đã dọn (quét 2026-10-27 trên `develop` f25b747)

| Domain | Lệch | Kết quả |
|---|---|---|
| copilot | `prompts/` ngoài khuôn; an toàn chia 2 nơi; `dispute_workflow` trong `engines/`; 4 cặp text trùng | ✅ |
| knowledge | `injection_scan.py` là luật an toàn nằm trong `engines/` | ✅ |
| knowledge_eval | prompt viết cứng (`judge.py:8`, `case_generator.py:11`) | ✅ (không thêm `dtos/` rỗng) |
| vision | 3 file ANPR ngoài `engines/anpr/`; luật biển số ở gốc `core/constants.py` | ✅ |
| forecast | `readers/` ngoài khuôn | ✅ chuyển vào `engines/`; tách I/O sang infra còn nợ |

### Chờ quyết (đã trả lời)

| Mã | Kết luận |
|---|---|
| OPEN-01 | `dispute/fixtures.py` là adapter hợp đồng cho endpoint mô phỏng, chủ đích khi workflow chưa nối backend (`arbitrate_dispute` vẫn `FeatureNotImplementedError`). Giữ trong `workflows/dispute/`, ghi ngoại lệ ở ADR-0005. |
| OPEN-02 | `PLATE_MIN_ALNUM = 6` là ngưỡng hợp lệ cứng (`is_valid_plate`), `_PLAUSIBLE_MIN_LEN = 7` là điểm cộng mềm (`is_plausible_plate_shape`). Hai luật khác nhau, không gộp; ghi chú ở `vision/constants.py`. |

### Còn lại (ngoài phạm vi refactor)

- Tách phần I/O của `forecast/engines/parquet_lake_reader.py` (689 dòng) sang `infra/datalake/`, giữ baseline + map DTO ở forecast.
- Chạy `redteam_copilot.py` khi có Ollama.
- Tách `console/services/tools_service.py` (870 dòng) nếu cần.

## Hồ sơ liên quan

- [ADR-0005](../../../adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md): quyết định khuôn
- [AI_CONVENTIONS §2](../../../../standards/AI_CONVENTIONS.md#2-khuôn-một-domain-trong-core)
- [review-1](review/review-1.md): báo cáo kiểm chứng
- [bug-042](../../../bugs/bug-042-prompt-copilot-khong-vao-image-chay-prompt-du-phong/bug.md): cổng vào chặng 0
- [ADR-0002](../../../adrs/10-2026/0002-tu-choi-khi-thieu-ngu-canh.md), [ADR-0003](../../../adrs/10-2026/0003-nguoi-duyet-truoc-khi-xu-ly-tranh-chap.md)
- IPLMS [ADR-0029](../../../../../../docs/projects/adrs/10-2026/0029-nguyen-tac-guardrail-llm.md): đổi prompt/guard phải chạy lại bộ tấn công
