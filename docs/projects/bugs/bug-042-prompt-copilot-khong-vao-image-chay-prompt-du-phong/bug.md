# 🐛 bug-042: Prompt Copilot không vào image, service âm thầm chạy prompt dự phòng

> **Đích:** `docs/projects/bugs/bug-042-prompt-copilot-khong-vao-image-chay-prompt-du-phong/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed — Đã sửa trong PR #112 (Copilot prompt nướng sẵn trong container image). |
| **Người nhận** | @khoalololo (Đỗ Minh Khoa — chủ module Copilot) |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | 2026-10-31 |
| **Người báo** | Claude Code (rà báo cáo Final theo đề §4.2) |
| **Môi trường** | local Docker (`iplms-ai-dev-api-1`), image build từ `Dockerfile` |

## Hành vi thực tế

`data/prompts/copilot_rag_system_v2.txt` đã nằm trong Git (commit `cd48d9d`), nhưng không tới được runtime:

- `Dockerfile.dockerignore` là allowlist, chỉ mở `ai/data/knowledge/*.json`, nên `COPY ai/data ./data` không chép `data/prompts/`.
- `.gitignore` có `data/*` mà không mở `data/prompts`, nên file chỉ vào repo nhờ `git add -f`; prompt phiên bản mới dễ bị bỏ sót.

`prompt_manager` không thấy file nên lặng lẽ dùng `DEFAULT_FALLBACK_PROMPT`, telemetry ghi `v1_fallback`. Đề Final §4.2 yêu cầu prompt lưu ở file có lịch sử Git: code đúng nhưng bản chạy thật không dùng nó.

## Hành vi mong đợi

Image chứa `data/prompts/*.txt`; `prompt_manager.get_metadata("copilot_rag_system")` trả `version=v2` và hash của file.

## Tái hiện

1. `docker exec -w /app iplms-ai-dev-api-1 python -c "from app.core.copilot.prompts import prompt_manager as m; print(m.get_metadata('copilot_rag_system'))"`
2. Kết quả: `{'version': 'v1_fallback', 'file_path': 'memory', 'hash': 'default'}`

## Bằng chứng

- `Dockerfile.dockerignore:10` — chỉ `!ai/data/knowledge/*.json`
- `Dockerfile:29` — `COPY ai/data ./data`
- `.gitignore:30` — `data/*`, không có `!data/prompts`
- `app/core/copilot/prompts/prompt_manager.py:67` — rơi về fallback, chỉ log warning

### Lỗi thứ hai cùng yêu cầu §4.2 (gộp vào hồ sơ này)

Đo lại chi phí/request cho báo cáo thì `usage` luôn rỗng với Ollama: nhánh Chat Completions của `LlmFactory.generate_response` (`app/infra/llm/llm_factory.py`) không chép `resp.usage`, còn `_copy_usage` chỉ đọc tên trường của Responses API (`input_tokens`/`output_tokens`), trong khi Chat Completions báo `prompt_tokens`/`completion_tokens`. Kết quả: `ai_request_log` không có token khi chạy provider mặc định.

## Sửa / kiểm chứng

| Thay đổi | File |
|---|---|
| Mở `!ai/data/prompts/*.txt` trong allowlist build | `Dockerfile.dockerignore` |
| `_copy_usage` nhận cả `prompt_tokens`/`completion_tokens`; nhánh Chat Completions gọi `_copy_usage` | `app/infra/llm/llm_factory.py` |
| Script eval ghi token từng câu, token + độ trễ trung bình mỗi request | `app/script/eval_copilot_e2e.py` |
| Test hồi quy | `test/test_docker_context.py` (thêm file prompt vào context), `test/test_llm_factory.py::test_compatible_endpoint_answer_reports_provider_tokens` |
| Ghi log AI + bảng chủ module | `AI_USAGE.md` |

Kiểm chứng (2026-10-27):

- `AI_RUN_CONTEXT_FIXTURE=1 python -m unittest test.test_docker_context`: **FAIL** với allowlist cũ, **OK** sau sửa (build Docker thật, `--network=none`).
- `python -m unittest test.test_llm_factory`: test mới **FAIL** trên `llm_factory.py` cũ, **OK** sau sửa.
- `python -m unittest discover -s test -t .`: 598 test, OK (36 skip) — chạy lại sau khi rebase lên develop f25b747.
- `prompt_manager` chạy từ worktree: `copilot_rag_system_v2#e88e1965` (không còn `v1_fallback`).

Eval đo lại 2026-10-27 (bge-m3 + qwen2.5:3b, Ollama local, pgvector tạm, 10 tài liệu demo của `seed_regulations`), chấm theo `expected_behavior`; từ chối chỉ tính khi hệ thống chặn:

| Bộ | Ngưỡng | Đạt | Từ chối đúng | Trả lời câu cần trả lời | Token TB/request (vào/ra) | Độ trễ TB |
|---|---|---|---|---|---|---|
| eval_set (27) | 0.35 | 21/27 | 2/7 | 19/20 | 1376 / 43 | 8.3 s |
| eval_set (27) | 0.55 | 23/27 | 6/7 | 17/20 | 981 / 35 | 4.8 s |
| eval_set_heldout (32) | 0.35 | 17/32 | 2/13 | 15/19 | 1409 / 40 | 8.5 s |
| eval_set_heldout (32) | 0.55 | 24/32 | 10/13 | 14/19 | 890 / 28 | 5.9 s |

Phát hiện thêm, chưa sửa (ngoài phạm vi): `expected_sources` trong hai bộ eval còn dùng tên nguồn của kho cũ (`*.pdf` và `demo_0N` khi seed có 7 đoạn); seed hiện có 10 đoạn nên tên `demo_0N_*` đã đổi, cột `group`/`source_hit` của `eval_copilot_e2e.py` không còn đúng. Cần chủ Copilot cập nhật bộ eval.

Chưa làm: chưa build lại image `iplms-ai` và chưa kiểm container dev (container hiện mount `data/` từ checkout khác). Ghi chú: `test_rag_pipeline.test_no_context_does_not_call_llm` và `test_copilot_usage.test_no_context` đỏ khi có `.env.dev` bật seed demo trong thư mục chạy test — test phụ thuộc file env, có sẵn từ trước, không do thay đổi này.
