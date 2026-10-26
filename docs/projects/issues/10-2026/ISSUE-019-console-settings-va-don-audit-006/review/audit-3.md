# 🔎 audit-3: Convention audit — AUDIT-006 WIP AI Console (soát lại vòng 3)

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Hồ sơ cha: [AUDIT-006](../../../../audits/10-2026/AUDIT-006-console-wip-2026-10-25.md). Vòng trước: [audit-2](audit-2.md) (không sửa file đó).

| | |
|---|---|
| **Kết luận** | ✅ Theo quyết định người dùng (2026-10-25): không còn P0/P1. P2/P3 còn mở chuyển `Deferred`, theo dõi ở các tiêu chí chưa tick của [ISSUE-019](../issue.md). A-23 chuyển sang [bug-029](../../../../bugs/bug-029-db-fallback-tu-tao-database-tren-postgres-khac/bug.md), A-33 sang [bug-028](../../../../bugs/bug-028-forecast-id-bai-lech-area-key/bug.md). A-22 vẫn chờ quyết. Fixer đã sửa A-54/A-55/A-48/A-56 sau vòng 3; phần này auditor **chưa soát lại** (xem mục cuối). |
| **Vòng** | 3/3 |
| **Người dùng quyết** | 2026-10-25: A-39 chọn B, giữ mặc định `llm_provider=ollama`, sửa test và DESIGN/`.env.example` cho khớp (người điều phối chuyển lời). |
| **Phạm vi** | `ai/` trên `develop`, WIP chưa commit. Index chưa stage gì (`git write-tree` = `8eaf427…`, trùng vòng 2), nên lệnh delta `git diff --cached` của vòng 2 rỗng. Vòng này soát theo danh sách file fixer khai: `app/config/runtime_override_config.py`, `app_config.py`, `console_config.py`, `console_main.py`, `console_tools_controller.py`, `tools_service.py` (settings, `_engine_status`, `_hardware_telemetry`), `llm_factory.py` (`_get_client`), `seed_console_demo.py`, `test/test_console_tools.py`, `test/test_llm_factory.py`, `ui/src/pages/Settings/SettingsPage.tsx`, `i18n/vi.ts`/`en.ts`, `tool.endpoint.ts`, `useToolMutations.ts`, `ChatMessageBubble.tsx`, `AI_CONVENTIONS.md`, `DESIGN.md`, `.env.example`, `app/core/copilot/README.md`, `.gitignore`. |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-25. Không phải người viết code hay fixer. |
| **Fixer** | Claude Code (phiên điều phối), theo mục "Đã sửa" của audit-2 |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py` (gốc IPLMS): 272 file, 0 FAIL, 2 WARN. Cả hai WARN thuộc `frontend/`. |
| **Quy ước đã nạp** | `ai/docs/standards/AI_CONVENTIONS.md` §1, §4, §6 · `ai/AGENTS.md` (DESIGN đi cùng thay đổi môi trường) · `ai/DESIGN.md` bảng env (dòng 257+) · `ai/ui` `ReasonAction` (step-up tại chỗ) · ADR-0048 §1, §4 |

## Kết quả chạy kiểm (vòng 3, 2026-10-25 khoảng 22:40)

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `python -X utf8 script/audit/check_diff.py` (gốc) | PASS: 0 FAIL. Phần `ai/` không có WARN. |
| Test backend | `ai/.venv/Scripts/python.exe -m unittest discover -s test` | **PASS**: 554 test, OK, 34 skip. |
| Tác dụng phụ | mtime `ai/var/runtime_settings.json` trước/sau suite | Không đổi: `2026-10-25 22:31:33.544` cả trước lẫn sau. File giờ nằm trong `.gitignore` (không hiện ở `git status`). |
| Typecheck UI | `npx tsc --noEmit` (ai/ui) | PASS (exit 0) |
| Test UI (vitest) | — | NOT RUN theo chỉ đạo (người điều phối chạy riêng). |
| Kiểm import | `python -c "import app.api.grpc.handlers.dataset_handler"` rồi liệt kê `sys.modules` | Nạp cả 8 service `app.core.console.services.*` (bằng chứng cho A-48). |
| Browser / DB / gRPC thật | — | NOT RUN, chỉ đọc code. Luồng ReasonAction + TOTP ở trang Settings và 422 của A-54 chưa thử trên browser. |

## Soát lại finding của vòng 2

| # | Mức | Loại | Trạng thái fixer | Trạng thái vòng 3 | Bằng chứng / lý do |
|---|---|---|---|---|---|
| A-5 | P1 | đúng-sai | Fixed (một phần) | **Verified** | Thông điệp đã nói đúng phạm vi áp dụng (`ui/src/i18n/vi.ts:1202`, `:1204`, `:1216`; `en.ts:1223`, `:1225`, `:1237`). File override hỏng thì bỏ cả file và log warning (`runtime_override_config.py:54-65`), có test `test_file_override_hong_khong_ap_do_dang` (`test_console_tools.py:300-315`). Lỗi ghi file được ném ra (`:70-82`). Phần S2 (DB có version, tự nạp lại) là đề xuất chứ không phải nội dung finding. Phát sinh một ca ngược chiều, ghi riêng ở A-53 (P3). |
| A-6 | P1 | bảo-mật | Fixed | **Verified** | Lý do bảo mật của finding là chuyển provider ra ngoài và đổi base_url mà không có step-up. Hai đường này đã đóng: `llm_provider: Literal["ollama","local"]` (`console_tools_controller.py:247`), service cũng từ chối (`tools_service.py:538-541`), `llm_model` có regex (`console_tools_controller.py:248`). Quyền compute vẫn là `ai:prompt:edit`/`ai:model:evaluate` và không step-up. Điều này chấp nhận được, vì giờ chỉ còn đổi qua lại giữa các engine chạy trên máy. Hồi quy: xem A-54. |
| A-38 | P1 | bảo-mật | Fixed | **Verified** | `llm_base_url` không còn trong DTO, cũng không còn trong `_FIELDS` (`runtime_override_config.py:28-47`). Khoá lạ có trong file cũ thì `apply_runtime_overrides` bỏ qua, vì hàm chỉ duyệt `_FIELDS` (`:58`). `persist_runtime_overrides` từ chối khoá lạ do code gửi vào (`:72-74`) nhưng vẫn giữ lại khoá cũ có sẵn trong file khi gộp (`:76-80`). Khoá đó vô hại vì không bao giờ được áp. `llm_factory.py` chỉ còn đọc `llm_base_url` từ env (`config.llm_base_url`). File thật hiện không còn `llm_base_url`. |
| A-46 | P2 | hợp-đồng | Fixed | **Verified** | Có enum ở DTO, UI đã bỏ `gemini` và khoá `openai` (`SettingsPage.tsx:452-454`). Không còn chỗ nào nhắc `gemini` trong `pages/Settings`, `services`, `hooks`, `types`. |
| A-43 | P1 | hợp-đồng | Fixed | **Verified** | `ReasonAction` (`SettingsPage.tsx:702-707`) nằm trong `<section>` (`:557`), không nằm trong `<form>`, nên không lồng form. Form compute (`:403-551`) là một khối riêng. `onStepUp` gọi `stepUp.mutateAsync({ code, reason })`, khớp `useStepUpMutation` (`useAuthMutations.ts:34-37`) và cách dùng ở `ModelsPage`/`DatasetsPage`. `ReasonAction` bắt `STEP_UP_REQUIRED` rồi hiện ô TOTP (`ReasonAction.tsx:19-26`, `:69-71`). `PolicySettingsIn.reason` bắt buộc (`console_tools_controller.py:266`). Caller duy nhất là `tool.endpoint.ts` `updatePolicySettings` (kiểu `{ reason: string }` bắt buộc), ngoài ra chỉ có test gọi service trực tiếp. Không caller nào bị gãy. Lưu ý: các ô số của policy giờ không còn nằm trong form nên mất kiểm `min`/`max` của HTML; giá trị lố biên vẫn bị DTO trả 422 và lỗi hiện trong `ReasonAction`. |
| A-42 | P2 | quy-ước | Fixed | **Verified** | Đã tách thành `app/config/runtime_override_config.py`. Biên kẹp khớp DTO, đã so từng trường (`:34-46` với `console_tools_controller.py:249-265`). Đường dẫn tuyệt đối theo `parents[2]` (`:15-18`). `app_config.py:33-37` chỉ còn gọi hàm. Cách đọc env của file này ghi ở A-56 (P3). |
| A-44 | P2 | test | Fixed | **Verified** | `setUp` patch `RUNTIME_SETTINGS_PATH` theo thuộc tính module, nên đúng cả khi path đã được tính lúc import. Test cũng patch `tools_service.get_config` sang `copy.deepcopy(get_config())` (`test_console_tools.py:257-277`). Deepcopy chạy được, suite xanh, và `get_config()` dùng chung không bị sửa. mtime file thật không đổi. `.gitignore` đã thêm hai file `var/`. |
| A-45 | P2 | quy-ước | Fixed | **Verified** | `SettingsPage.tsx:461`, `:472` dùng `s.llmModelLabel`/`s.llmModelRunning`, có ở cả `vi.ts:1194-1195` và `en.ts:1215-1216`. Vitest do người điều phối chạy. |
| A-26 | P2 | hiệu-năng | Fixed | **Verified** | `asyncio.to_thread(_engine_status, …)` ở `tools_service.py:225` (`system_check`) và `:502` (`get_runtime_settings`). `_hardware_telemetry` cũng chạy qua thread (`:474`). |
| A-49 | P3 | đúng-sai | Fixed | **Verified** | `tools_service.py:144-145`: thông điệp đúng nội dung, mức `debug`. |
| A-47 | P2 | đúng-sai | Fixed | **Verified** | `ConsoleConfig.reload=False` (`console_config.py:24`, prefix `AI_CONSOLE_`, tức `AI_CONSOLE_RELOAD`). `console_main.py:139-142` không còn đọc `os.environ`. Compose chạy bằng entrypoint `uvicorn app.console_main:app` (`docker-compose.yml:104`), không đi qua `__main__`, nên không bị ảnh hưởng. Biến mới chưa có trong tài liệu (A-56). |
| A-50 | P3 | hợp-đồng | Fixed | **Verified** | `session_id: UUID` (`console_tools_controller.py:327`), service nhận `str(session_id)`. |
| A-7 | P2 | đúng-sai | Fixed (một phần) | **Phần cổng Verified · phần metrics còn Open** | `check_environment` (`seed_console_demo.py:628-634`) bắt buộc `demo_seed_enabled` và không còn coi thiếu env là dev. Cờ này đọc qua `get_config()` (BaseConfig đọc cả `.env.dev`). Không tài liệu nào hướng dẫn chạy `seed_console_demo` (grep không thấy), nên không có chỗ nào lệch hướng dẫn demo. **Còn mở:** đoạn ghi đè `eval_run.metrics` rồi propose/promote, fixer ghi là chờ người giữ WIP quyết. |
| A-52 | P3 | quy-ước | Fixed | **Verified** | `seed_knowledge_base` (`seed_console_demo.py:151-181`) không còn đoạn mở kết nối rồi `pass`. |
| A-48 | P3 | tài-liệu | Fixed | **Reopened** (lần 1) | Câu nhắc `app/dependencies.py` đã bỏ. Nhưng lý do ghi cho ngoại lệ inline import ở `AI_CONVENTIONS.md:60` ("để không nạp `app.core.console` khi process khởi động") **sai với code hiện tại**: `app/api/grpc/mappers/dataset_mapper.py:1` (WIP) import `app.core.console.dtos` ở đầu file, và lệnh này chạy `app/core/console/__init__.py:2-13`, nạp cả 8 service console. Đã kiểm bằng `import app.api.grpc.handlers.dataset_handler`: `sys.modules` có đủ `app.core.console.services.*`. Ngoài ra hai dòng import ở `dataset_mapper.py:1-2` nằm trên docstring, làm docstring mất tác dụng. Cách sửa: hoặc ghi đúng lý do (chỉ còn là tránh vòng import), hoặc đổi `dataset_mapper.py` sang import `ExportedCapture` từ `app.core.console.dtos.<module>` theo kiểu trễ, để lý do trong quy ước đúng thật. |
| A-51 | P3 | quy-ước | Fixed | **Verified** | `ChatMessageBubble.tsx:144`, `:158`, `:172`, `:191` có `aria-label` lấy từ i18n. Nút ✕ có `aria-label={t.copilot.cancel}` (`:272`). |
| A-41 | P2 | hiệu-năng | Fixed (một phần) | **Còn Open** | URL health đã lấy theo `local_url` và chỉ dò khi provider là `local` (`llm_factory.py:96-104`). **Còn:** `urllib.request.urlopen` đồng bộ (timeout 0.3 s) vẫn chạy trong đường async khi provider là `local`. Việc bỏ `llama_server_manager.ensure_server_running()` chưa ghi ở DESIGN, trong khi `docs/projects/KHOA_MODULE_GUIDE.md:240`, `:292` vẫn mô tả `ensure_server_running()` được gọi. |
| A-39 | P1 | đúng-sai | Cần quyết → người dùng chọn B | **Verified** (theo quyết định B) | `DESIGN.md` (bảng env: `AI_LLM_PROVIDER=ollama`, `AI_OLLAMA_URL`, `AI_LLM_MODEL=qwen2.5:0.5b`, key chỉ bắt buộc khi `openai`), `.env.example:51-57`, `app/core/copilot/README.md:57` khớp nhau. Test cũ khai rõ `provider="openai"` và vẫn kiểm `ModelNotLoadedError`. `active_prov = self.provider or provider`, nên provider của factory thắng provider trong config. Test mới `test_default_ollama_provider_uses_placeholder_key_without_probe` patch `urlopen` và assert không gọi tới. Unit test không còn gọi mạng tới 8005. |
| A-11/12, A-23, A-25, A-33, A-37, A-40 | P2/P3 | — | Open (chưa làm) | **Còn Open** | Fixer chưa chạm. Giữ nguyên mô tả ở audit-2, không nêu lại. |
| A-22 | — | quy-ước | Cần quyết | Cần quyết | Không đổi. |

## Finding mới vòng 3 (A-53 trở đi, chỉ trong hunk fixer chạm)

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái |
|---|---|---|---|---|---|---|---|
| A-53 | P3 | đúng-sai | `app/core/console/services/tools_service.py:510-551` → `:566`; `:578-595` → `:597` | DESIGN Hallmark 2 (không báo sai trạng thái) | Service sửa `get_config()` trong bộ nhớ trước, rồi mới gọi `persist_runtime_overrides`. Nếu ghi file thất bại (đĩa, quyền, JSON cũ hỏng làm `json.load` ném lỗi ở `runtime_override_config.py:78-79`), API trả lỗi nhưng console **vẫn chạy với giá trị mới** cho tới lần khởi động lại. Đây là ca ngược của A-5: báo lỗi trong khi đã áp. Thêm vào đó, file được ghi thẳng bằng `open("w")` (`runtime_override_config.py:81-82`), không ghi tạm rồi thay, nên process chết giữa chừng sẽ để lại file hỏng. | Tính giá trị mới vào dict, `persist` trước, thành công mới `setattr` (hoặc hoàn tác khi lỗi). Ghi file qua tệp tạm rồi `os.replace`. | Open |
| A-54 | P2 | hợp-đồng | `ui/src/pages/Settings/SettingsPage.tsx:90`, `:131`; `app/api/rest/routes/console_tools_controller.py:247` | Hợp đồng hai đầu (convention-audit §3.2) | Hồi quy do A-6/A-46 gây ra. Khi env đặt `AI_LLM_PROVIDER=openai`, GET trả `llm_provider="openai"`, UI nạp giá trị đó vào state (`:90`, select hiện option bị disabled), và `submitCompute` **luôn** gửi `llm_provider: llmProvider` (`:131`). DTO `Literal["ollama","local"]` trả 422, nên **cả form compute** (thiết bị vision, ONNX, GPU layers, threads…) không lưu được trên môi trường dùng OpenAI. Test không phủ ca này. | Chỉ gửi `llm_provider` khi giá trị thuộc `ollama`/`local` (hoặc khi người dùng đổi), hoặc để BE bỏ qua provider không đổi so với cấu hình hiện tại. Thêm test (FE hoặc route) cho ca env `openai`. | Open |
| A-55 | P3 | đúng-sai | `app/core/console/services/tools_service.py:513`, `:520`, `:527`, `:563-566` | Ghi chú của chính hunk (`:563`) và DESIGN bảng env ("`openai` chỉ bật qua env") | Ba preset gán cứng `llm_provider="local"`, rồi giá trị này được ghi xuống file. Môi trường đặt `AI_LLM_PROVIDER=openai` bấm preset sẽ lặng lẽ chuyển sang local, và từ lần khởi động sau file thắng env, nên đặt env không còn tác dụng. Comment ở `:563` ("Provider OpenAI đặt qua env thì không ghi đè thành provider local") chỉ đúng cho nhánh không dùng preset. Hướng chuyển là về local nên không lộ dữ liệu, nhưng trái với mô tả env là nguồn quyết định provider. | Preset không đổi provider khi provider hiện tại không phải local, hoặc báo rõ trên UI rằng preset sẽ chuyển sang local và ghi đè env. | Open |
| A-56 | P3 | tài-liệu | `app/config/runtime_override_config.py:15-18`; `app/config/console_config.py:23-24`; `DESIGN.md:257` | `ai/AGENTS.md` "cập nhật DESIGN… cùng thay đổi"; DESIGN:257 "Danh sách biến chuẩn nằm trong `.env.example`"; AI_CONVENTIONS §4 (đọc cấu hình qua `get_config`) | Hai biến mới `AI_RUNTIME_SETTINGS_PATH` và `AI_CONSOLE_RELOAD` chưa có trong `.env.example` hay bảng env của DESIGN. Hành vi file override (`var/runtime_settings.json` thắng env, inference chỉ nhận sau khi khởi động lại) cũng chưa ghi ở DESIGN. Ngoài ra `AI_RUNTIME_SETTINGS_PATH` được đọc bằng `os.environ.get` lúc import, đi vòng `BaseConfig`, nên đặt biến này trong `.env.dev` sẽ không có tác dụng (khác mọi biến `AI_*` khác). | Thêm hai biến vào `.env.example` và bảng env của DESIGN, kèm một dòng về file override. Đưa path vào một `BaseConfig` (ví dụ `ConsoleConfig.runtime_settings_path`), hoặc ghi rõ ngoại lệ. | Open |

### Theo loại (Open + Reopened, sau vòng 3)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| đúng-sai | 0 | 0 | 3 (A-7 phần metrics, A-23, A-40) | 2 (A-53, A-55) |
| bảo-mật | 0 | 0 | 1 (A-37) | 0 |
| hợp-đồng | 0 | 0 | 2 (A-11/12, A-54) | 0 |
| test | 0 | 0 | 1 (A-25) | 0 |
| hiệu-năng | 0 | 0 | 1 (A-41) | 0 |
| quy-ước | 0 | 0 | 0 | 1 (A-33) |
| tài-liệu | 0 | 0 | 0 | 2 (A-48 Reopened, A-56) |
| **Tổng** | **0** | **0** | **8** | **5** |

Verified vòng 3: A-5, A-6, A-38, A-39, A-42, A-43, A-44, A-45, A-46, A-26, A-47, A-49, A-50, A-51, A-52 (cộng phần cổng của A-7). Cần quyết: A-22.

## WARN đã xét

| WARN | Kết luận | Lý do |
|---|---|---|
| `FE-DEFAULT-EXPORT frontend/packages/client/.../PublicLayout.tsx:22`, `.../PaymentModal.tsx:286` | Ngoài phạm vi | Thuộc repo `frontend/`, không thuộc WIP `ai/` của AUDIT-006. |

## Bug đã mở

Không mở theo chỉ đạo của người điều phối. Nếu người dùng cho phép thì nên mở `bug-NNN` (namespace `ai/docs`) cho A-54 (form compute hỏng trên môi trường dùng OpenAI) và A-23 (tự `CREATE DATABASE` trên Postgres fallback). Trước khi mở cần tìm trùng ở `ai/docs/projects/bugs/` và BOARD.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `docker-compose.yml:120` đặt `AI_CONSOLE_DEMO_SEED_ENABLED=true` ở compose **base**, trong khi `DESIGN.md:13` ghi "base/production mặc định tắt". File này không có trong WIP; ghi lại để chủ dự án xem.
- `app/core/console/__init__.py:2-13` nạp sẵn mọi service (đã ghi ở audit-2). Giờ đã có bằng chứng là process inference nạp chúng qua `dataset_mapper.py:1`, xem A-48.

## Soát lại

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 1 | 2026-10-25 | (không ghi, file audit-1 đã mất) | A-1..A-37 | 1 P0, 6 P1, 20 P2, 10 P3 Open (theo hồ sơ cha) |
| 2 | 2026-10-25 | `8eaf42716ed99afa6abfd07ef9bd30a300a9ddde` | BUG-01..12, A-20..A-37 và hunk mới | Open: 5 P1, 13 P2, 6 P3 |
| 3 | 2026-10-25 | `8eaf42716ed99afa6abfd07ef9bd30a300a9ddde` (index vẫn chưa stage gì; soát theo danh sách file fixer khai) | 17 finding Fixed / Fixed một phần / A-39, cùng hunk fixer chạm | 15 Verified, A-7 và A-41 còn phần mở, A-48 Reopened lần 1. Thêm 4 finding mới (A-53..A-56; 1 P2, 3 P3). Còn mở: 0 P1, 8 P2, 5 P3. **⛔ Hết 3 vòng** |

## Sửa sau vòng 3 (fixer, 2026-10-25, chưa stage, chưa commit)

Chỉ sửa phần do lượt sửa trước gây ra. Không mở vòng 4; auditor hoặc người dùng soát lại khi stage.

| # | Đã sửa | Bằng chứng |
|---|---|---|
| A-54 | UI chỉ gửi `llm_provider` khi giá trị là `ollama`/`local`, nên env `openai` không còn bị 422. | `ui/src/pages/Settings/SettingsPage.tsx` (`submitCompute`) |
| A-55 | Preset chỉ đặt `local` khi provider hiện tại là local/ollama, không lặng lẽ đổi OpenAI. Sửa comment cho khớp. | `tools_service.py` (3 nhánh preset) |
| A-48 | Đưa `console_vision_import_service` và `console_accept_policy_service` lên đầu `dataset_handler.py`: đã thử import, không có vòng import. AI_CONVENTIONS bỏ ngoại lệ gRPC, giữ một ngoại lệ là thư viện ML nặng. | `dataset_handler.py:20-21`, `docs/standards/AI_CONVENTIONS.md:60` |
| A-56 | Thêm `AI_CONSOLE_RELOAD` và `AI_RUNTIME_SETTINGS_PATH` vào `.env.example` và bảng env của DESIGN, ghi rõ path chỉ đọc từ env thật. | `.env.example`, `DESIGN.md` |
| A-53 | Chưa sửa (P3): cấu hình đổi trong RAM trước khi ghi file. | — |

Kiểm: unittest 554 OK (34 skip) · `tsc --noEmit` PASS · vitest như ghi ở chat.

## Quyết định của người dùng (2026-10-25)

Nguyên văn yêu cầu: "Các P2 còn mở (A-7 metrics seed, A-11/12, A-25, A-37, A-40, A-41, A-53) cho Deferred, theo dõi ở tiêu chí chưa tick của ISSUE-019; A-22 vẫn chờ quyết."

| # | Trạng thái sau quyết định | Theo dõi ở |
|---|---|---|
| A-7 (phần ghi đè metrics eval), A-11/12, A-25, A-37, A-40, A-41, A-53 | Deferred | ISSUE-019, tiêu chí "P2 còn mở" |
| A-23 | Deferred → hồ sơ riêng | bug-029 |
| A-33 | Deferred → hồ sơ riêng | bug-028 |
| A-22 | Cần quyết | ISSUE-019, tiêu chí A-22 |
| A-48, A-54, A-55, A-56 | Fixed sau vòng 3, auditor chưa soát lại; kiểm lại bằng unittest 554 OK, tsc PASS, vitest 93/93 | Soát lại ở PR vào `develop` |

