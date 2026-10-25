# 🔎 audit-2: Convention audit — AUDIT-006 WIP AI Console (soát lại vòng 2)

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Hồ sơ cha: [AUDIT-006](../../../../audits/10-2026/AUDIT-006-console-wip-2026-10-25.md). File chi tiết vòng 1 (`AUDIT-006-audit-1.md`) đã mất, nên mã A-n của vòng 1 lấy theo bảng BUG-01..12 trong hồ sơ cha.

| | |
|---|---|
| **Kết luận** | ❌ Còn finding mở: 5 P1, 13 P2, 6 P3, cộng 1 cần quyết |
| **Vòng** | 2/3 |
| **Phạm vi** | `ai/` trên `develop` (HEAD `af92e76`), WIP chưa commit: 100 file, +5042/−503, cộng các file untracked `app/script/seed_console_demo.py`, `ui/src/constants/parkingLots.ts`, `ui/src/pages/Settings/`, `var/runtime_settings.json`. Không có delta so với vòng 1 vì vòng 1 không ghi `Tree`. Vòng này soát lại các finding đã nêu, cộng các hunk Settings/LLM/DB/seed theo yêu cầu người điều phối. |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-25. Không phải người viết code. |
| **Fixer** | Chưa ghi tên (WIP sửa tiếp sau 18:27 tới khoảng 20:30) |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py` (gốc IPLMS): 269 file, 0 FAIL, 2 WARN. Cả hai WARN thuộc `frontend/`, không thuộc `ai/`. |
| **Quy ước đã nạp** | `ai/docs/standards/AI_CONVENTIONS.md` §1–§4, §8 · `ai/ui/DESIGN.md` (i18n, Hallmark 2/8, Step-up tại chỗ) · `app/core/console/engines/access_policy.py` (STEP_UP_PERMISSIONS, ADR-0048 §4) · ADR-0029 (guardrail LLM) |

## Kết quả chạy kiểm (vòng 2, 2026-10-25 khoảng 22:20)

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `python -X utf8 script/audit/check_diff.py` | PASS: 0 FAIL. Phần `ai/` không có WARN. |
| Test backend | `ai/.venv/Scripts/python.exe -m unittest discover -s test` | **FAIL**: 551 test, 1 failure, 34 skip. Test hỏng là `test_llm_factory.LlmProviderTest.test_missing_key_without_base_url_is_precondition_error` (xem A-39). |
| Typecheck UI | `npx tsc --noEmit` (ai/ui) | PASS (exit 0) |
| Test UI | `npx vitest run --maxWorkers=1 --no-file-parallelism` | **FAIL**: 19 file, 93 test, 1 failure. Test hỏng là `src/i18n/noHardcodedVi.test.ts`: `SettingsPage.tsx:461`, `:472` (xem A-45). |
| Browser / DB / gRPC thật | — | NOT RUN, chỉ đọc code. Gap giữ như §5 của hồ sơ cha. |

> **Tác dụng phụ đã quan sát:** chạy unittest đã ghi lại `ai/var/runtime_settings.json`. mtime của file là 22:21:14, đúng lúc suite chạy, và nội dung hiện là `rag_min_similarity: 0.6`, `rag_top_k: 7`, tức giá trị của test. Auditor không hoàn tác vì không biết nội dung trước đó. Người giữ WIP cần xem lại file này trước khi khởi động console hoặc inference (A-44).

## Findings

Trạng thái: `Open` · `Đã hết` (đã kiểm trên code hiện tại, tương đương `Verified`) · `Cần quyết` (chờ người dùng hoặc ADR).

### Finding vòng 1 (BUG-01..12 và các A được nêu)

| # | BUG | Mức | Loại | `file:line` hiện tại | Luật | Mô tả hiện trạng | Cách sửa đề xuất | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| A-1 | BUG-01 | P0 | đúng-sai | `app/api/grpc/handlers/dataset_handler.py:73`, `:85` | — | Inline import đã được đưa lại. `git diff` của file chỉ còn khác CRLF. Có test `test_console_tools.py:295` gọi `GetAcceptPolicy`. | — | Đã hết |
| A-2 | BUG-02 | P1 | đúng-sai | `console_tools_controller.py:294-298` → `auth_service.py:176-182` | ADR-0048 §4 | `/settings/policy` đã đổi sang `require_permission("ai:policy:threshold")`. Hàm này đi qua `authorize` và bắt step-up đúng cách, không còn bị 400 cứng. | — | Đã hết |
| A-3 | BUG-03 | P1 | bảo-mật | `app/infra/database/console_vision_store.py:338-366`, `:398-403` | Bốn mắt (`access_policy.require_second_person`) | `add_label` không còn rẽ nhánh riêng cho mẫu demo. Seed chọn người gán là thành viên khác người bấm (`id <> actor`). | — | Đã hết |
| A-4 | BUG-04 | P1 | bảo-mật | `app/infra/database/db_connection.py:11-22`, `:130` | CLAUDE.md, Redaction | Log khi tự tạo DB thất bại đã qua `_redact_url`. | — | Đã hết |
| A-5 | BUG-05 | P1 | đúng-sai | `ui/src/i18n/vi.ts:1199`, `app/config/app_config.py:34-83`, `tools_service.py:192-204` | DESIGN Hallmark 2 (không báo giả) | Đã đỡ hơn: file override được đọc khi tạo `AppConfig`, và lỗi ghi được log thay vì `pass`. **Vẫn còn:** UI báo "Đã lưu **và áp dụng**", trong khi process inference (8000) chỉ thấy thay đổi sau khi khởi động lại. Ngoài ra `reload_runtime_overrides` nuốt lỗi bằng `except Exception: pass` (`app_config.py:82`), nên nếu file JSON hỏng ở giữa thì cấu hình được áp dở dang mà không ai biết. | Báo đúng trạng thái áp dụng ("Đã áp cho console, inference cần khởi động lại") theo S2. Log hoặc cảnh báo khi đọc override thất bại. | Open |
| A-6 | BUG-06 | P1 | bảo-mật | `console_tools_controller.py:283-291`, `tools_service.py:522-524`, `:555-560` | ADR-0048 §4 (thao tác nhạy cảm cần step-up và lý do) | Phần policy đã sửa. **Còn lại phần compute:** `llm_provider` (chuyển sang `openai`, tức gửi câu hỏi ra ngoài), `llm_model` và `llm_base_url` đổi được chỉ với `ai:prompt:edit` **hoặc** `ai:model:evaluate`, không step-up, không lý do. Cấu hình này còn được lưu xuống file và nạp lại cho cả process inference. | Tách đổi provider/base_url sang quyền step-up (ví dụ `ai:policy:threshold` hoặc một quyền mới), bắt lý do, ghi giá trị trước-sau vào audit. | Open |
| A-7 | BUG-07 | P2 (hạ từ P1) | đúng-sai | `app/script/seed_console_demo.py:634-640`, `:563-581` | AI_CONVENTIONS §4, §8 | Đã bỏ `DELETE … ARCHIVED` và không còn chèn lượt đã chấm CORRECT. **Vẫn còn:** cổng chặn mặc định coi là `development` khi `ENVIRONMENT`/`APP_ENV` không được đặt, nên vẫn chạy được trên một DB thật thiếu biến. Script còn ghi đè `eval_run.metrics` bằng số bịa ("metrics thực tế đẹp") rồi `propose`/`promote` model dựa trên số đó. | Mặc định là từ chối: chỉ chạy khi `demo_seed_enabled` bật **và** env thuộc danh sách dev. Không sửa `eval_run.metrics` bằng tay; nếu cần dữ liệu demo thì ghi rõ là demo. | Open |
| A-8 | BUG-08 | P2 | hợp-đồng | `ui/src/pages/Copilot/components/ChatStudio/ChatStudio.tsx:99`, `:234` | — | Tin nhắn bot đã mang `userQuery`, và ô "Đưa vào Eval" giờ lấy câu hỏi gốc. Còn fallback `message.content` ở `ChatMessageBubble.tsx:29`, `:64` cho tin không có `userQuery`, nhưng không chặn. | (Tuỳ chọn) bỏ fallback sang `content`. | Đã hết |
| A-9 | BUG-09 | P2 | đúng-sai | `tools_service.py:651-664`, `auth_service.py:167`, `console_store.py:557-580` | — | `ConsoleActor.session_id` được gắn từ `get_session` (`id::text`) nên `is_current` đúng. Tự thu hồi phiên đang dùng bị chặn ở service, và UI ẩn nút (`SettingsPage.tsx:758`). | — | Đã hết |
| A-10 | BUG-09 | P2 | bảo-mật | `console_tools_controller.py:320-329` | — | Endpoint revoke không còn nhận `ai:task:label`. Người không phải admin/lead chỉ thu hồi được phiên của chính mình (`console_store.py:598-602`). | — | Đã hết |
| A-11/A-12 | BUG-12 | P2 | hợp-đồng | `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx:55-59`, `:316`; `tools_service.py:438-444`, `:453`, `:466` | DESIGN Hallmark 2; AUDIT-006 S5 | Kiểu FE vẫn khai `predicted_vehicles`, trong khi BE trả `estimated_free_spots`, `surge_multiplier`, `confidence`. `model_version` vẫn là hằng `"lightgbm-prophet-v1.4"` ở BE, FE tự đặt mặc định `'lightgbm-prophet-baseline-v1.0'`, và `records_count` mặc định là 168. `is_fallback` có trong kiểu nhưng không được hiển thị ở đâu. Test `test_forecast_simulation_schema_alignment` chỉ kiểm khoá của `surge_quote`, không kiểm `hourly_predictions`. | Đồng bộ kiểu theo dict BE. Lấy `model_version` từ artifact, thiếu thì `—`. Hiện nhãn "Dữ liệu mô phỏng" khi `is_fallback`. Mở rộng test sang `hourly_predictions`. | Open |
| A-17 | BUG-10 | P2 | đúng-sai | `ui/src/pages/Copilot/components/ReviewForm.tsx:35-43` | — | Phím tắt bỏ qua khi có Ctrl/Alt/Meta/Shift, khi đang `isPending`, khi focus nằm trong ô nhập, và khi lượt đã có verdict. | — | Đã hết |
| A-20 | — | — | quy-ước | `app/api/rest/router.py:6-16` | ADR-0048 §1 | `router.py` chỉ còn đổi thứ tự import và thêm `__all__`, không kéo mã console vào process inference. | — | Đã hết |
| A-21 | — | — | quy-ước | (file `app/dependencies.py` đã xoá) | AI_CONVENTIONS §1 | File phá bảng tầng không còn. Tài liệu vẫn nhắc tới nó (A-48). | — | Đã hết |
| A-22 | — | — | quy-ước | `app/infra/database/pgvector_client.py:98-101` | Cổng schema (skill iplms-schema-design) | Fallback cột `DOUBLE PRECISION[]` cùng hàm SQL `iplms_cosine_sim` vẫn còn và chưa qua cổng schema. | Người dùng hoặc ADR quyết có cho phép chế độ không có pgvector hay không. | Cần quyết |
| A-23 | BUG-11 | P2 | đúng-sai | `app/infra/database/db_connection.py:58`, `:107-130`, `:177` | — | Đã đổi để thử 5435 trước. **Vẫn còn:** khi 5435 không lên, code fallback sang 5432 (một Postgres khác trên máy dev) và **tự `CREATE DATABASE`** ở đó. Nhánh này cũng áp cho URL gốc của mọi môi trường. | Chỉ tự tạo DB khi URL ứng viên trùng URL cấu hình và đang ở môi trường dev. Không tự tạo trên ứng viên fallback. | Open |
| A-25 | — | P2 | test | `test/test_console_tools.py:253-315` | AI_CONVENTIONS (Kiểm chứng) | Đã thêm 5 test ở mức service. **Thiếu:** test qua HTTP route (lớp `require_permission`/step-up, `ComputeSettingsIn`, `/sessions/{id}/revoke`) và test `ExportForConsole`. Test policy thì gọi service thật nên để lại tác dụng phụ (A-44). | Thêm test `TestClient` cho các route Settings/Sessions, kiểm `STEP_UP_REQUIRED`, và một test cho `ExportForConsole`. | Open |
| A-26 | — | P2 | hiệu-năng | `app/core/console/services/tools_service.py:519` → `:56-59`; `:242` | AI_CONVENTIONS §6 | `_hardware_telemetry` đã chạy qua `asyncio.to_thread` (`:491`). **Vẫn còn:** `_engine_status` `import torch` và gọi `torch.cuda.is_available()` đồng bộ trong event loop, ở cả `get_runtime_settings` lẫn `system_check`. | Gọi `_engine_status` qua `asyncio.to_thread`, hoặc chỉ đọc `importlib.metadata`. | Open |
| A-33 | — | P3 | quy-ước | `ui/src/constants/parkingLots.ts:9-15`; `ForecastSimulator.tsx:74-95` | AUDIT-006 S8 | Ba danh sách đã gộp về một hằng chung, nhưng vẫn là danh sách cứng chứ không lấy từ API. ForecastSimulator còn giữ một chuỗi lấp đầy cứng cho từng bãi (`LOT_OCCUPANCY_BASELINES`). | Lấy danh sách bãi từ API hoặc fixture chung. | Open |
| A-37 | — | P2 | bảo-mật | `app/core/console/services/copilot_lab_service.py:118-137`, `:147` | ADR-0029 (đầu vào độc mặc định); telemetry chỉ lưu `query_redacted` | `var/eval_candidates.json` vẫn lưu câu hỏi thô ngoài DB, không có retention. Audit summary còn chép thêm `clean_query[:80]`. | Lưu vào bảng DB có retention, dùng bản đã redact như `ai_request_log`. Bỏ câu hỏi khỏi audit summary. | Open |

### Finding mới vòng 2 (A-38 trở đi)

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái |
|---|---|---|---|---|---|---|---|
| A-38 | P1 | bảo-mật | `console_tools_controller.py:247`, `tools_service.py:559-560`, `app/config/app_config.py:53-54` | CLAUDE.md "STRICT PRIVACY" (không gửi dữ liệu ra ngoài); ADR-0029 | `llm_base_url` nhận **URL bất kỳ** (chỉ giới hạn 256 ký tự, không allowlist). Giá trị này được ghi vào `var/runtime_settings.json` và cả hai process nạp lại khi khởi động. Kết quả: câu hỏi người dùng cùng ngữ cảnh RAG có thể bị đẩy sang một host lạ, và server bị dùng làm SSRF. UI không có ô này, nhưng gọi thẳng API thì vẫn đổi được. | Allowlist host (loopback, `ollama_url`, `local_llm_url` từ env) hoặc bỏ hẳn `llm_base_url` khỏi API; chỉ đổi qua env. | Open |
| A-39 | P1 | đúng-sai | `app/config/llm_config.py:36`; `app/infra/llm/llm_factory.py:135`; `test/test_llm_factory.py:64-68` | Hợp đồng ISSUE-011 (thiếu key thì báo lỗi rõ) | Mặc định `llm_provider` đổi từ `local` sang `ollama`, nên khi thiếu `AI_LLM_API_KEY` thì không còn `ModelNotLoadedError`: code lặng lẽ gọi `127.0.0.1:11434`. Test hồi quy **FAIL**, và trong lúc chạy còn gửi HTTP thật tới `127.0.0.1:8005/health`. Môi trường nào quên đặt `AI_LLM_PROVIDER=openai` sẽ hỏng âm thầm. | Giữ fail-loud: chỉ dùng Ollama khi provider được khai rõ. Hoặc sửa test cùng quyết định, kèm ghi DESIGN. Không gọi mạng trong unit test. | Open |
| A-40 | P2 | đúng-sai | `app/config/llm_config.py:25`, `:51-52`; `llm_factory.py:58-59`, `:131-132`, `:389-390`; `SettingsPage.tsx:472` | DESIGN Hallmark 2; ai bug-018 (không bịa) | `active_model_name` giờ luôn trả `llm_model` (mặc định `qwen2.5:0.5b`), nên nhánh tên GGUF không bao giờ chạy tới. Khi llama-server chạy Qwen3.5-4B, telemetry, `system_check` và dòng "Model đang chạy" vẫn báo `qwen2.5:0.5b`. Thêm vào đó, chuỗi cứng `"gpt-5.6-luna"`, `"Qwen3.5-4B-Q4_K_M"` và `"qwen2.5:0.5b"` lặp ở 5 chỗ để ép model. | Lấy tên model thật từ provider (`/v1/models`) hoặc từ cấu hình đang dùng. Gom hằng về `app/core/constants.py` hoặc config. | Open |
| A-41 | P2 | hiệu-năng | `app/infra/llm/llm_factory.py:94-101` | AI_CONVENTIONS §4 (đọc cấu hình qua `get_config`) | `_get_client` gọi `urllib.request.urlopen("http://127.0.0.1:8005/health")` đồng bộ, với URL cứng không theo `local_llm_url`. Hàm này được gọi từ các đường async (`:194`, `:278`, `:312`, `:349`), và `eval_service.py:103` cùng `model_policy_service.py:32` tạo factory mới ở mỗi lượt, nên lượt nào cũng có thể chặn event loop tới 0.3 giây. Ngoài ra `llama_server_manager.ensure_server_running()` đã bị bỏ: provider `local` không còn tự bật server. Đây là thay đổi hành vi chưa thấy ghi ở DESIGN (câu hỏi). | Dò health bằng client async, URL lấy từ `local_llm_url`, có cache. Xác nhận việc bỏ auto-start và ghi vào DESIGN. | Open |
| A-42 | P2 | quy-ước | `app/config/app_config.py:34-83` | AI_CONVENTIONS §4 [MUST] "thêm nhóm cấu hình mới = thêm một file trong `app/config/`, không nhét vào `app_config.py`" | `reload_runtime_overrides` gồm 20 trường, nằm thẳng trong `app_config.py`. Giá trị đọc từ file không được kẹp biên như ở service (ví dụ `rag_min_similarity`, `telemetry_retention_days`). Đường dẫn tương đối `var/…` phụ thuộc CWD. | Tách thành `runtime_override_config.py`, validate bằng pydantic dùng chung biên với `ComputeSettingsIn`/`PolicySettingsIn`, và dùng đường dẫn tuyệt đối từ config. | Open |
| A-43 | P1 | hợp-đồng | `ui/src/pages/Settings/SettingsPage.tsx:141-160`, `:557`, `:701` | `ai/ui/DESIGN.md` "Step-up tại chỗ" (thao tác nhạy cảm đi qua `Ui/form/ReasonAction`) | Sau khi BE bắt step-up cho `ai:policy:threshold`, form policy vẫn submit thẳng. Lead nhận `STEP_UP_REQUIRED` chỉ dưới dạng `ErrorBlock`, không có ô nhập TOTP và lý do, nên không lưu được ngưỡng từ trang này. Lỗi phát sinh do hai đầu sửa lệch nhau. | Bọc nút lưu policy bằng `ReasonAction` (TOTP và lý do), giống luồng duyệt ngưỡng hiện có. | Open |
| A-44 | P2 | test | `test/test_console_tools.py:257-265`; `tools_service.py:192-204`, `:612`; `.gitignore` | Test không được ghi dữ liệu thật (AGENTS "ca biên thử trên bản sao") | Test gọi `update_policy_settings` thật. Lời gọi này đổi `get_config()` dùng chung (lru_cache) cho các test sau, **và ghi `ai/var/runtime_settings.json` thật**: đã quan sát lúc 22:21:14 trong lượt chạy của vòng này, file hiện chứa `rag_min_similarity=0.6`, `rag_top_k=7`. Mọi process nạp file này khi khởi động. File `var/runtime_settings.json` cũng chưa có trong `.gitignore`. | Patch `_RUNTIME_SETTINGS_PATH` sang thư mục tạm và dùng bản sao config trong test. Thêm `var/runtime_settings.json` và `var/eval_candidates.json` vào `.gitignore`. | Open |
| A-45 | P2 | quy-ước | `ui/src/pages/Settings/SettingsPage.tsx:461`, `:472` | `ai/ui/DESIGN.md` i18n; bug-023 (`noHardcodedVi.test.ts`) | Có chữ tiếng Việt viết thẳng trong TSX, làm vitest FAIL. | Chuyển sang `t.settings.*` ở `vi.ts`/`en.ts`. | Open |
| A-46 | P2 | hợp-đồng | `SettingsPage.tsx:455`; `console_tools_controller.py:246`; `tools_service.py:555-556`; `llm_factory.py:26`, `:91` | Hợp đồng hai đầu (convention-audit §3.2) | UI cho chọn `gemini`, BE nhận provider là chuỗi tự do và không có nhánh nào cho `gemini`, nên rơi vào đường OpenAI Responses với key OpenAI. Gửi `llm_provider` lạ cũng không bị từ chối. | Khai enum `Literal["ollama","local","openai"]` ở DTO, và bỏ `gemini` khỏi UI (hoặc cài thật). | Open |
| A-47 | P2 | đúng-sai | `app/console_main.py:138-144` | AI_CONVENTIONS §4 [NEVER] đọc `os.environ` rải rác | Không đặt `ENVIRONMENT` thì console chạy với `reload=True` (reloader theo dõi file). Process đó vì thế là bản dev, kể cả trên máy chủ thật. Biến môi trường cũng được đọc thẳng thay vì qua `get_config()`. | Mặc định không reload; chỉ bật qua cờ cấu hình rõ ràng (ví dụ `AI_CONSOLE_RELOAD`) trong `console_config`. | Open |
| A-48 | P3 | tài-liệu | `docs/standards/AI_CONVENTIONS.md:60` | — | Quy ước mới nhắc tới "container DI tập trung `app/dependencies.py`", nhưng file đã bị xoá. Luật mới "không inline import `from app…`" cũng mâu thuẫn với `dataset_handler.py:73`, `:85`, là chỗ vừa phải giữ inline import để sửa A-1. | Bỏ phần nhắc `app/dependencies.py`, ghi ngoại lệ cho handler gRPC (hoặc lý do vòng import). | Open |
| A-49 | P3 | đúng-sai | `app/core/console/services/tools_service.py:146-147` | — | Khi `torch` hoặc CUDA lỗi, log ghi "Không thể lưu cấu hình runtime settings" (dán nhầm thông báo), và câu này lặp lại ở mỗi lần GET Settings. | Sửa thông điệp, hạ xuống debug hoặc chỉ log một lần. | Open |
| A-50 | P3 | hợp-đồng | `console_tools_controller.py:323-324`; `console_store.py:596-602` | — | `session_id` ở path không được kiểm là UUID. Truyền chuỗi lạ thì Postgres ném `invalid input syntax for type uuid` và trả 500. | Khai `session_id: UUID` ở route. | Open |
| A-51 | P3 | quy-ước | `ui/src/pages/Copilot/components/ChatStudio/ChatMessageBubble.tsx:139`, `:153`, `:166`, `:182`, `:270` | Cổng chất lượng L5 (a11y) | Input/select của hộp "Đưa vào Eval" chỉ có `<span>` làm nhãn, không có `<label htmlFor>` hay `aria-label`. Nút huỷ `✕` không có tên accessible. | Dùng `<label>` + `useId`, thêm `aria-label={t.copilot.cancel}`. | Open |
| A-52 | P3 | quy-ước | `app/script/seed_console_demo.py:154-160` | CLAUDE.md Surgical/Simplicity | Đoạn mở kết nối DB rồi `pass` không làm gì (code chết). | Xoá đoạn này. | Open |

### Theo loại (chỉ tính Open)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| đúng-sai | 0 | 2 (A-5, A-39) | 4 (A-7, A-23, A-40, A-47) | 1 (A-49) |
| bảo-mật | 0 | 2 (A-6, A-38) | 1 (A-37) | 0 |
| hợp-đồng | 0 | 1 (A-43) | 2 (A-11/12, A-46) | 1 (A-50) |
| test | 0 | 0 | 2 (A-25, A-44) | 0 |
| hiệu-năng | 0 | 0 | 2 (A-26, A-41) | 0 |
| quy-ước | 0 | 0 | 2 (A-42, A-45) | 3 (A-33, A-51, A-52) |
| tài-liệu | 0 | 0 | 0 | 1 (A-48) |
| **Tổng** | **0** | **5** | **13** | **6** |

Đã hết: A-1, A-2, A-3, A-4, A-8, A-9, A-10, A-17, A-20, A-21. Cần quyết: A-22.

## WARN đã xét

| WARN | Kết luận | Lý do |
|---|---|---|
| `FE-DEFAULT-EXPORT frontend/packages/client/.../PublicLayout.tsx:22`, `.../PaymentModal.tsx:286` | Ngoài phạm vi | Thuộc repo `frontend/`, không thuộc WIP `ai/` của AUDIT-006. |

## Bug đã mở

Không mở theo chỉ đạo của người điều phối. Nên mở `bug-NNN` (namespace `ai/docs`) cho các finding chạy sai: A-5, A-6, A-38, A-39, A-43 (P1), cùng A-23 và A-44 (ghi dữ liệu thật).

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `app/core/console/__init__.py:2-14`: package nạp sẵn mọi service console khi bị import. Hiện chưa gây lỗi; ghi lại để theo dõi vòng import với `dataset_handler`.

## Đã sửa (fixer, 2026-10-25 ~22:40, chưa stage, chưa commit)

Fixer: Claude Code (phiên điều phối, không phải auditor). Auditor vòng 3 đặt `Verified`/`Reopened`.

| # | Trạng thái | Đã sửa | Bằng chứng |
|---|---|---|---|
| A-5 | Fixed (một phần) | Thông báo ở UI nói rõ "console áp dụng ngay, inference nhận sau khi khởi động lại". File hỏng thì bỏ cả file và log warning, không áp dở dang. Lỗi ghi file giờ ném ra, API không còn báo lưu giả. **Chưa làm:** S2 (lưu DB có version, inference tự nạp lại). | `app/config/runtime_override_config.py`, `ui/src/i18n/vi.ts` (`savedComputeMsg`, `savedPolicyMsg`, `policyFormSub`), test `test_file_override_hong_khong_ap_do_dang` |
| A-6 + A-38 + A-46 | Fixed | `ComputeSettingsIn.llm_provider` thành `Literal["ollama","local"]`. Bỏ `llm_base_url` khỏi API và khỏi file override. Service từ chối provider không phải local. OpenAI (gửi câu hỏi ra ngoài) chỉ bật qua env. UI bỏ `gemini`, khoá lựa chọn `openai`. `llm_model` giới hạn ký tự bằng regex. | `console_tools_controller.py:247-248`, `tools_service.py` (`update_compute_settings`), `SettingsPage.tsx`, test `test_compute_khong_doi_sang_provider_ngoai` |
| A-43 | Fixed | Form policy dùng `ReasonAction` kèm `onStepUp` (TOTP + lý do tại chỗ). `PolicySettingsIn.reason` bắt buộc (3–500 ký tự), lý do được ghi vào audit summary. | `SettingsPage.tsx` (`submitPolicy`), `console_tools_controller.py:266`, `tools_service.py` (summary policy) |
| A-42 | Fixed | Override tách sang `app/config/runtime_override_config.py`: một bảng trường, kẹp biên giống DTO, đường dẫn tuyệt đối theo gốc `ai/` (env `AI_RUNTIME_SETTINGS_PATH`). `app_config.py` chỉ còn gọi `apply_runtime_overrides`. | `app/config/runtime_override_config.py`, `app/config/app_config.py:34-36` |
| A-44 | Fixed | Test Settings chạy trên file tạm và bản sao config (`setUp`/`tearDown`). Thêm `var/runtime_settings.json` và `var/eval_candidates.json` vào `.gitignore`. Đã gỡ khỏi file thật các khoá test để lại (`rag_min_similarity=0.6`, `rag_top_k=7`) cùng `llm_base_url`. | `test/test_console_tools.py` (`ConsoleSettingsAndToolsEndpointTest.setUp`), `.gitignore`; suite chạy xong mtime file thật không đổi |
| A-45 | Fixed | Hai chuỗi VI chuyển sang `t.settings.llmModelLabel` / `llmModelRunning`. | `vitest` 93/93 PASS |
| A-26 | Fixed | `_engine_status` chạy qua `asyncio.to_thread` ở `system_check` và `get_runtime_settings`. | `tools_service.py` |
| A-41 | Fixed (một phần) | URL health lấy từ `local_llm_url`, chỉ dò khi provider là `local` (không dò khi dùng `ollama`). **Còn:** lời gọi vẫn đồng bộ; chưa ghi DESIGN về việc bỏ auto-start llama-server. | `llm_factory.py` (`_get_client`) |
| A-47 | Fixed | Reload chỉ bật qua `AI_CONSOLE_RELOAD=true` (`ConsoleConfig.reload`, mặc định False). Bỏ đọc `os.environ` trong `console_main.py`. | `app/config/console_config.py`, `app/console_main.py` |
| A-49 | Fixed | Log lỗi torch sửa đúng nội dung, hạ xuống debug. | `tools_service.py` (`_hardware_telemetry`) |
| A-50 | Fixed | `session_id: UUID` ở route revoke, chuỗi lạ trả 422 thay cho 500. | `console_tools_controller.py:327` |
| A-7 | Fixed (một phần) | Mặc định từ chối: luôn phải bật `AI_CONSOLE_DEMO_SEED_ENABLED`, thiếu `ENVIRONMENT` không còn bị coi là dev. **Còn:** đoạn ghi đè `eval_run.metrics` rồi propose/promote, chờ người giữ WIP quyết. | `seed_console_demo.py` (`check_environment`) |
| A-52 | Fixed | Xoá đoạn mở kết nối DB rồi `pass`. | `seed_console_demo.py` (`seed_knowledge_base`) |
| A-48 | Fixed | AI_CONVENTIONS bỏ phần nhắc `app/dependencies.py`, ghi ngoại lệ inline import cho handler gRPC. | `docs/standards/AI_CONVENTIONS.md:60` |
| A-51 | Fixed | Thêm `aria-label` cho input/select của hộp "Đưa vào Eval" và cho nút ✕. | `ChatMessageBubble.tsx` |
| A-39 | Cần quyết | Không sửa. Mặc định `ollama` trái với DESIGN.md:267 và `.env.example` (`gpt-5.6-luna`, fail-loud khi thiếu key). Cần chủ dự án chọn; xem báo cáo trong chat. | `test_llm_factory` vẫn FAIL 1 |
| A-11/12, A-23, A-25 (route), A-33, A-37, A-40 | Open | Chưa làm ở lượt này. | — |

Kiểm sau khi sửa: unittest 553 test, 1 FAIL (chỉ A-39), 34 skip · `npx tsc --noEmit` PASS · vitest 93/93 PASS · `check_diff.py` 0 FAIL (2 WARN thuộc `frontend/`).

## Soát lại

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-25 | (không ghi, file audit-1 đã mất) | A-1..A-37 | 1 P0, 6 P1, 20 P2, 10 P3 Open (theo hồ sơ cha) |
| 2 | 2026-10-25 | `8eaf42716ed99afa6abfd07ef9bd30a300a9ddde` (index, chưa stage gì) | BUG-01..12, A-20/21/22/25/26/33/37 và hunk mới Settings/LLM/DB/seed/UI | 10 Đã hết · 1 Cần quyết · Open: 5 P1, 13 P2, 6 P3 (gồm 15 finding mới A-38..A-52) |

Vòng 3 sẽ soát delta `git diff --cached 8eaf427 -- . ':!docs/projects/audits/10-2026/AUDIT-006-audit-2.md'` (fixer phải stage phần sửa), cùng các finding chuyển `Fixed`.
