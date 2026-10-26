# 📐 ADR-0002: Copilot từ chối khi không có ngữ cảnh đủ gần, không cho LLM tự suy luận

> **Đích:** `docs/projects/adrs/10-2026/0002-tu-choi-khi-thieu-ngu-canh.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Accepted |
| **Ngày** | 2026-10-26 |
| **Người quyết định** | HiTranquility (chọn viết ADR thật cho hồ sơ Final Project, [bug-032](../../bugs/bug-032-ho-so-final-project-lech-voi-repo/bug.md)) |
| **Phạm vi** | IPLMS-AI: `app/core/copilot/` (RAG pipeline, guardrail), `data/prompts/` |

## Bối cảnh

Copilot trả lời câu hỏi về quy chế và biểu phí bãi xe. Mô hình nhỏ chạy local (Qwen 0.5B–4B) hay "chiều" người hỏi: hỏi giá mà ngữ cảnh không có giá thì nó vẫn đưa ra một con số. Với bãi xe, một mức phí hay chính sách đền bù bịa ra là rủi ro tiền và pháp lý, tệ hơn hẳn một câu "chưa có thông tin".

Quyết định này đã có trong code từ trước, nhưng hồ sơ nộp bài gọi nó là "ADR-0008" mà không có file. ADR-0008 của repo gốc IPLMS là quyết định khác (bộ skill).

## Quyết định

"Thà từ chối hơn bịa." LLM chỉ được gọi khi truy xuất ra ngữ cảnh đủ gần câu hỏi:

1. Không có chunk nào → trả `NO_CONTEXT_ANSWER`, không gọi LLM (`rag_pipeline.py`, `_grounded_chunks`).
2. Có chunk nhưng độ tương đồng cao nhất dưới `AI_RAG_MIN_SIMILARITY` (mặc định **0.35**, `app/config/llm_config.py`) → `GuardrailManager.check_scope_and_chunks` từ chối với nhãn `OUT_OF_SCOPE`.
3. Khi đã gọi LLM, prompt hệ thống (`data/prompts/copilot_rag_system_v2.txt`) buộc chỉ dùng NGỮ CẢNH ĐÃ TRUY XUẤT, trích `[Nguồn: …]`, và nói rõ khi ngữ cảnh không đủ.
4. Seed demo chỉ lấp chỗ trống khi bật `AI_CONSOLE_DEMO_SEED_ENABLED=true` (dev/sandbox); production không có chunk thì vẫn `NO_CONTEXT`.

Ngưỡng và prompt là một cặp: đổi một trong hai thì chạy lại bộ eval (`data/knowledge/eval_set.json`) và `python -m app.script.redteam_copilot` (IPLMS ADR-0029 luật 5).

## Các phương án đã cân nhắc

- **A. Để LLM tự quyết khi nào nói "không biết".** Ít code, nhưng mô hình nhỏ làm việc này không ổn định và không kiểm được bằng test xác định. Không chọn.
- **B. Ngưỡng cao hơn (0.5 trở lên).** Giảm thêm rủi ro bịa nhưng từ chối nhầm câu hỏi hợp lệ diễn đạt khác tài liệu. Giữ 0.35 làm mặc định; ngưỡng cấu hình được theo môi trường.

## Hệ quả

### Được

- Câu hỏi ngoài phạm vi bị chặn trước khi tốn lượt gọi LLM; hành vi kiểm được bằng unit test không cần model.
- Log telemetry ghi `status` (`NO_CONTEXT` / `REFUSED`) và `prompt_version`, nên đếm được tỉ lệ từ chối theo từng phiên bản prompt.

### Đánh đổi

- Câu hỏi đúng chủ đề nhưng kho tri thức chưa có tài liệu sẽ bị từ chối: phải bổ sung tài liệu, không chỉnh prompt.
- Ngưỡng phụ thuộc model embedding; đổi model embedding thì phải đo lại ngưỡng.

## Bằng chứng và liên kết

- Code: `app/core/copilot/guardrails/guardrail_manager.py` (`check_scope_and_chunks`), `app/core/copilot/engines/rag_pipeline.py`, `app/config/llm_config.py` (`rag_min_similarity`), `data/prompts/copilot_rag_system_v2.txt`.
- Test: `test/test_rag_pipeline.py`, `test/test_copilot_streaming_api.py` (từ chối câu ngoài phạm vi); bộ eval `data/knowledge/eval_set.json`.
- Liên quan: IPLMS ADR-0029 (guardrail LLM: ngữ cảnh là dữ liệu, không phải chỉ dẫn).
