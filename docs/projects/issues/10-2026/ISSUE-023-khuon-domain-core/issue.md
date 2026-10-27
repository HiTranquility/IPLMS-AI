# 🏷️ ISSUE-023: Đưa `app/core/` về khuôn domain của ADR-0005 (prompt ra `data/prompts/`, slot tuỳ chọn có tên cố định)

> **Đích:** `docs/projects/issues/10-2026/ISSUE-023-khuon-domain-core/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 📝 Draft (chờ bug-042 merge vào `develop`) |
| **Người nhận** | @HiTranquility |
| **Hạn** |  |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** |  |
| **Người phụ trách** | HiTranquility |
| **Phạm vi** | IPLMS-AI: `app/core/**`, `app/infra/llm/`, `app/infra/datalake/`, `data/prompts/`, `test/`, `app/script/`, `script/` |

## Mục tiêu

Mọi domain trong `app/core/` theo đúng khuôn ở [ADR-0005](../../../adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md): ba thư mục lõi, chỉ dùng slot tuỳ chọn có tên trong danh sách, text gửi LLM nằm ở `data/prompts/`, không còn bản chép trùng. Đây là refactor: **hành vi ra ngoài không đổi** (proto, REST, câu trả lời, nhãn `promptVersion`).

## Tiêu chí chấp nhận

- [ ] `script/check_core_layout.py` chạy trên `develop` sau merge: 0 thư mục/file ngoài khuôn, 0 prompt viết cứng trong `app/core/`; có test và chạy trong CI.
- [ ] `data/prompts/` có `copilot_rag/`, `eval_judge/`, `eval_generator/`; mỗi prompt có version + hash trong telemetry; không còn `DEFAULT_FALLBACK_PROMPT`, thiếu file thì khởi động báo lỗi.
- [ ] `llm_factory.py` dựng user message từ **một** khuôn (hiện chép 3 lần ở :202, :262, :435).
- [ ] `NO_CONTEXT_ANSWER`, `GUARD_NOTICE` và marker từ chối chỉ khai một lần trong `copilot/messages.py`; `grader.py` và `eval_copilot_e2e.py` import từ đó; có test đỏ khi đổi câu trả lời mẫu mà không đổi marker.
- [ ] Nhãn `promptVersion` trả về backend giữ dạng `<tên>_<version>#<hash8>`; caller NestJS không phải sửa.
- [ ] `python -m unittest discover -s test` xanh sau **mỗi** chặng; `app/script/redteam_copilot.py` chạy lại sau chặng chạm guard/prompt (luật IPLMS ADR-0029).
- [ ] AI_CONVENTIONS §2 khớp code (cập nhật `verified-against-code`).

## Kế hoạch

Mỗi chặng là một commit riêng trên nhánh `feature/ISSUE-023-2026-10-khuon-domain-core`; chặng sau chỉ bắt đầu khi chặng trước xanh.

0. **Cổng vào.** bug-042 merge vào `develop`; working tree `ai/` hết merge dở; rebase nhánh này lên `develop`. → kiểm: `git log origin/develop --oneline | grep bug-042`, `git status` sạch.
1. **Luật + máy kiểm.** ADR-0005, AI_CONVENTIONS §2 (đã làm trong lượt tạo hồ sơ). Viết `script/check_core_layout.py` + `test/test_check_core_layout.py`, lúc đầu chạy chế độ báo cáo (in danh sách lệch hiện tại, chưa chặn CI). → kiểm: script liệt kê đúng các lệch ở bảng dưới.
2. **copilot** (lớn nhất, đụng nhiều nhất):
   - Prompt: `data/prompts/copilot_rag_system_v2.txt` → `data/prompts/copilot_rag/v2.md` + `user.md` (khuôn CÂU HỎI/NGỮ CẢNH); `core/copilot/prompts/prompt_manager.py` → `infra/llm/prompts.py`; bỏ fallback.
   - `llm_factory.py` dùng một khuôn từ `user.md`; `redteam_copilot.py:42` (`_FORGED`) dựng từ cùng khuôn.
   - `messages.py`: `NO_CONTEXT_ANSWER` (gộp `rag_pipeline.py:27` + `guardrail_manager.py:50`), `GUARD_NOTICE`, `REFUSAL_MARKERS`.
   - `guardrails/`: `guardrail_manager.py` + `engines/output_guard.py` + `engines/pii_redactor.py`; `console` import `redact` qua `app.core.copilot`.
   - `engines/rag/` từ `rag_pipeline.py` (592 dòng, tách theo bước: truy xuất / gate / gọi LLM / trích nguồn).
   - `workflows/dispute/` từ `engines/dispute_workflow/`; `fixtures.py` chờ OPEN-01.
   → kiểm: unittest đủ bộ, redteam, so `promptVersion` trước/sau.
3. **knowledge + knowledge_eval:** `injection_scan.py` → `knowledge/guardrails/` (copilot `workflows/dispute/nodes.py` import qua `app.core.knowledge`); `JUDGE_INSTRUCTIONS`, `GENERATOR_INSTRUCTIONS` + schema → `data/prompts/eval_judge/`, `eval_generator/`; `grader.py` và `app/script/eval_copilot_e2e.py` dùng `copilot.messages.REFUSAL_MARKERS`; thêm `knowledge_eval/dtos/` nếu có DTO thật. → kiểm: unittest, chạy một lượt eval nhỏ.
4. **vision:** gom `anpr_engine.py` (façade), `anpr_onnx_engine.py`, `two_line_plate_parser.py` vào `engines/anpr/`; `vision/constants.py` nhận ngưỡng từ `preprocess.py:11-31`, `scoring.py:16-17`, `plate_text.py:7-21` và `PLATE_MAX_LENGTH`, `PLATE_MIN_ALPHA`, `PLATE_MIN_ALNUM`, `PLATE_OCR_ALLOWLIST` (chỉ vision dùng); `FALLBACK_PLATE_NUMBER` ở lại `core/constants.py` (dataset + util dùng). Kiểm OPEN-02. → kiểm: unittest vision, benchmark ANPR không đổi kết quả trên bộ golden.
5. **forecast + console:** `forecast/readers/parquet_lake_reader.py` → `infra/datalake/`; xoá `forecast/engines/` rỗng (tạo lại khi có model); `console/dtos/` khi có DTO thật. → kiểm: unittest forecast, `test_lakehouse_forecast_e2e`.
6. **Bật chặn:** `check_core_layout.py` chuyển sang chế độ fail trong CI; cập nhật `verified-against-code` của AI_CONVENTIONS; báo cáo `review/review-1.md`.

### Lệch hiện tại (quét 2026-10-27 trên `develop` f25b747)

| Domain | Lệch | Chặng |
|---|---|---|
| copilot | `guardrails/`, `prompts/` ngoài khuôn cũ; an toàn chia 2 nơi; `dispute_workflow` trong `engines/`; 4 cặp text trùng | 2 |
| knowledge | `injection_scan.py` là luật an toàn nằm trong `engines/` | 3 |
| knowledge_eval | prompt viết cứng (`judge.py:8`, `case_generator.py:11`); thiếu `dtos/` | 3 |
| vision | 3 file ANPR ngoài `engines/anpr/`; ngưỡng rải 4 nơi | 4 |
| forecast | `readers/` ngoài khuôn; `engines/` rỗng | 5 |
| console | thiếu `dtos/` | 5 |

### Chờ quyết

| Mã | Câu hỏi | Ảnh hưởng |
|---|---|---|
| OPEN-01 | `copilot_service.py:17` import `ContractEvidenceClient`… từ `dispute_workflow/fixtures.py` ở runtime. Adapter thật nối backend đã có chưa, hay đây là chủ đích (ADR-0003)? | Chuyển `fixtures.py` sang `test/` sẽ gãy service nếu chưa có adapter thật |
| OPEN-02 | `PLATE_MIN_ALNUM = 6` (`core/constants.py:12`) và `_PLAUSIBLE_MIN_LEN = 7` (`plate_text.py:7`): cùng đo một thứ hay hai luật khác nhau (hợp lệ vs khả tín)? | Gộp sai thì đổi kết quả ANPR |

### Ngoài phạm vi

- Tách `console/services/tools_service.py` (870 dòng): ghi việc riêng nếu cần.
- Đổi tên domain, đổi proto: ADR-0005 giữ nguyên tên.

## Hồ sơ liên quan

- [ADR-0005](../../../adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md): quyết định khuôn
- [AI_CONVENTIONS §2](../../../../standards/AI_CONVENTIONS.md#2-khuôn-một-domain-trong-core)
- [bug-042](../../../bugs/bug-042-prompt-copilot-khong-vao-image-chay-prompt-du-phong/bug.md): cổng vào chặng 0
- [ADR-0002](../../../adrs/10-2026/0002-tu-choi-khi-thieu-ngu-canh.md), [ADR-0003](../../../adrs/10-2026/0003-nguoi-duyet-truoc-khi-xu-ly-tranh-chap.md)
- IPLMS [ADR-0029](../../../../../../docs/projects/adrs/10-2026/0029-nguyen-tac-guardrail-llm.md): đổi prompt/guard phải chạy lại bộ tấn công
