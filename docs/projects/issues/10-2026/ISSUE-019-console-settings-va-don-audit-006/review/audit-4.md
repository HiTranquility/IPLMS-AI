# 🔎 audit-4: Convention audit — ISSUE-019 sửa các finding Deferred (A-53, A-11/12, A-40, A-25)

> Mẫu của [convention audit](../../../../../../../skills/iplms-code-review/references/convention-audit.md) (IPLMS ADR-0052). Auditor viết; fixer chỉ sửa cột "Đã sửa" và trạng thái `Fixed`; auditor đặt `Verified`/`Reopened` và Kết luận.
> Vòng trước: [audit-3](audit-3.md) (3/3, không sửa file đó). Hồ sơ: [ISSUE-019](../issue.md).

| | |
|---|---|
| **Kết luận** | ✅ Đạt sau soát lại (2026-10-26, lượt 6): trong delta không còn P0–P2 Open/Reopened. A-40 đã Verified theo hướng A đổi nhãn mà người dùng chọn. A-61 (P3) còn Open, không chặn. A-60 (P3, FAIL NAMING) nằm ngoài phạm vi, Deferred: sẽ hết khi rename ISSUE-007 → ISSUE-011 được stage ở commit riêng. |
| **Vòng** | 4 (sau 3/3 của audit-3). Lượt này mở vì người dùng đã quyết ở audit-3 (2026-10-25: nhận Deferred) và fixer sửa tiếp phần Deferred. Đây không phải vòng sửa mới được cấp. |
| **Người dùng quyết** | 2026-10-26 (lần 2): A-40 chọn hướng A theo cách đổi nhãn (b). 2026-10-26: chọn hướng A (sửa tiếp A-11/12, A-40, A-58, A-57, A-59), người điều phối chuyển lời. 2026-10-25 (ghi ở audit-3): A-7 phần metrics, A-11/12, A-25, A-37, A-40, A-41 và A-53 chuyển `Deferred`, theo dõi ở ISSUE-019. Lượt này chưa có quyết định mới. |
| **Phạm vi** | `ai/`, nhánh `feature/ISSUE-019-2026-10-console-settings-audit-006`, HEAD `d55ac7c`, delta `git diff HEAD` (chưa stage). Có 10 file theo danh sách người điều phối giao: `app/config/runtime_override_config.py`, `app/config/llm_config.py`, `app/infra/llm/llm_factory.py`, `app/core/console/services/tools_service.py`, `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx`, `ui/src/i18n/vi.ts`, `ui/src/i18n/en.ts`, `test/test_console_tools.py`, `test/test_console_settings_http.py` (mới). Các file khác trong working tree không thuộc phạm vi. |
| **Auditor** | Claude Code, subagent auditor độc lập, 2026-10-25. Không viết code và không sửa chặng này. |
| **Fixer** | Claude Code (phiên điều phối) |
| **Máy quét** | `python -X utf8 script/audit/check_diff.py --repo ai` (chạy từ gốc IPLMS): 274 file, **1 FAIL**, 2 WARN (lượt 4) · cũng 1 FAIL (A-60), 2 WARN (lượt 5). FAIL là NAMING, nằm ngoài danh sách file được giao (A-60). Cả hai WARN thuộc `frontend/`. |
| **Quy ước đã nạp** | `ai/docs/standards/AI_CONVENTIONS.md` §4 (cấu hình), mục Kiểm chứng · `ai/DESIGN.md` Hallmark 2 (không bịa số, không báo sai trạng thái) · `ai/ui/DESIGN.md` (i18n, token) · convention-audit §3.2 (đọc hợp đồng ở cả hai đầu) |

## Kết quả chạy kiểm (2026-10-25, khoảng 23:30)

| Lớp | Lệnh | Kết quả |
|---|---|---|
| Máy quét | `python -X utf8 script/audit/check_diff.py --repo ai` | 1 FAIL (NAMING: `ISSUE-007` trùng), 2 WARN `frontend/` |
| Test backend | `ai/.venv/Scripts/python.exe -m unittest discover -s test` | **PASS**: 562 test, OK, 34 skip. Vòng trước có 554 test, lượt này thêm 8. |
| Tác dụng phụ | mtime `ai/var/runtime_settings.json` trước và sau suite | Không đổi: `2026-10-25 22:31:33.544`. Trong `var/` không còn file `.tmp`. |
| Typecheck UI | `npx tsc --noEmit` (ai/ui) | PASS (exit 0) |
| Vitest | — | NOT RUN theo chỉ đạo (người điều phối chạy). |
| Browser / llama-server / Ollama thật | — | NOT RUN, chỉ đọc code. Máy này không có `model/checkpoint/llm/` nên nhánh GGUF của `active_model_name` không chạy được ở đây. Chưa thử `os.replace` trên Windows khi một process khác đang mở file đích. |

## Soát lại finding

| # | Mức | Loại | Trạng thái trước | Trạng thái lượt này | Bằng chứng / lý do |
|---|---|---|---|---|---|
| A-53 | P3 | đúng-sai | Deferred | **Verified** | `snapshot_runtime_fields`/`restore_runtime_fields` (`runtime_override_config.py:70-77`) duyệt hết `_FIELDS`, trong đó có `llm_provider` (`:33`). Vì vậy rollback khôi phục cả provider. Mọi thuộc tính mà `_apply_compute` gán (`tools_service.py:531-576`) đều nằm trong `_FIELDS`. Nhánh ném `ValueError` ở `:563-564`, xảy ra sau khi đã gán `vision_device`, giờ cũng được hoàn tác. Policy cũng được bọc như vậy (`:597-631`). File được ghi qua tệp tạm rồi `os.replace` (`runtime_override_config.py:92-95`). Trên Windows, nếu một process khác đang mở file đích mà không có `FILE_SHARE_DELETE` (đây là mặc định của `open()` trong Python), `os.replace` sẽ ném `PermissionError`. Lỗi được ném lên, RAM được hoàn tác, API báo lỗi đúng. Process inference chỉ giữ file trong lúc đọc khi khởi động, nên khoảng va chạm hẹp. Chỗ còn hở ghi ở A-57 (P3). Có test `test_ghi_file_loi_thi_hoan_tac_cau_hinh` (`test_console_tools.py:300-313`), độ chặt của test ghi ở A-59. |
| A-11/12 | P2 | hợp-đồng | Deferred | **Reopened (lần 1)** | Đã đạt: kiểu `hourly_predictions` khớp dict BE (`ForecastSimulator.tsx:55-61` so với `tools_service.py:427-433`). Hằng `lightgbm-prophet-*` và số 168 ở FE đã bỏ. `model_version` không còn bịa tên LightGBM. Test kiểm khoá `hourly_predictions`. Bỏ `toUpperCase` cũng đúng, vì `PARKING_LOTS` dùng id chữ thường và reader so khớp phân biệt hoa thường (`parquet_lake_reader.py:124`). **Chưa đạt:** `tools_service.py:441` đọc `training_data.get("records_count", 0)`, nhưng `filter_training_dataset` trả khoá **`total_records`** (`parquet_lake_reader.py:612`). Khoá `records_count` không tồn tại, nên `stage1_datalake.total_records` luôn bằng **0** và UI hiện "0 (7 × 24h)" (`ForecastSimulator.tsx:280`). Trước đây là số 168 bịa, giờ là số 0 sai, cùng một lỗi Hallmark 2. Test không kiểm giá trị này. Cách sửa: đọc `training_data.get("total_records", 0)`, rồi thêm assert `total_records > 0` (hoặc bằng số bản ghi baseline) vào `test_forecast_simulation_schema_alignment`. |
| A-40 | P2 | đúng-sai | Deferred | **Reopened (lần 1)** | Đã đạt: hằng được gom về `llm_config.py:9-11`, `llm_factory.py` dùng hằng (`:59`, `:135`). Stream giờ gửi `model=self.model` (`:393`), giống `generate_answer` (`:225`) và `generate_json`/`_generate_json_via_chat` (`:259`, `:314`, lấy `model or self.model`). `self.model` đã được ép ở `__init__` (`:59-61`) khi provider factory là local/ollama, và được ép lại ở nhánh rơi sang Ollama (`:135-136`), nên không còn hai cách chọn model lệch nhau. Khi provider là openai, kết quả `active_model_name` giữ như cũ: hàm trả `llm_model` (kể cả `gpt-5.6-luna`), rỗng thì trả mặc định. **Hồi quy mới ở nhánh GGUF** (`llm_config.py:56-57`): khi `llm_provider == "local"` và file GGUF tồn tại, `active_model_name` trả tên file GGUF và **bỏ qua `llm_model`**. Hệ quả: (1) Khi llama-server chưa bật, `_get_client` rơi sang Ollama (`llm_factory.py:111-137`). Lúc đó, tên GGUF mặc định nằm trong `NON_OLLAMA_MODEL_NAMES`, nên factory ép về `qwen2.5:0.5b` thay vì dùng model người dùng chọn ở Settings. Còn tên GGUF khác (đặt qua `AI_LOCAL_LLM_MODEL_PATH`) thì được gửi thẳng cho Ollama và nhận `ModelConfigurationError`. Code cũ dùng `llm_model` ở cả hai trường hợp. (2) Trong trường hợp đó, `get_runtime_settings` (`tools_service.py:490`) và `system_check` (`:225`) vẫn báo "Model đang chạy" là tên GGUF, trong khi Ollama đang chạy một model khác. Đây chính là lỗi A-40 muốn đóng. (3) `SettingsPage.tsx:91` nạp `comp.llm_model` (tức tên GGUF) vào ô nhập, rồi `:133` luôn gửi lại giá trị đó. Lưu bất kỳ trường compute nào cũng ghi đè `llm_model` của người dùng bằng tên GGUF (`tools_service.py:583`), và sau khi lưu, ô nhập trở về tên GGUF nên trông như thay đổi không có tác dụng. Không có test cho nhánh GGUF hay nhánh openai của `active_model_name`. Cách sửa: tách hai khái niệm. Model gửi đi lấy `llm_model` (ép theo provider như hiện nay). Tên hiển thị lấy từ client thực tế đã chọn: factory ghi lại nhánh llama, Ollama hay OpenAI, hoặc `system_check` hỏi `/v1/models`. GET settings trả `llm_model` cấu hình riêng với `llm_model_running`. Thêm test cho ba provider. |
| A-25 | P2 | test | Deferred | **Verified** | `test/test_console_settings_http.py` gọi route thật qua `TestClient(app.console_main.app)`, chỉ giả lập `console_auth_service.resolve` và service. Test phủ các ca: thiếu step-up thì nhận `STEP_UP_REQUIRED` và service không được gọi (`:52-56`); thiếu `reason` thì 422; `ai_ml_engineer` gửi policy thì 403; compute gửi `llm_provider=openai` thì 422; `llm_base_url` bị `extra="ignore"` bỏ đi và không tới service; `ai_annotator` GET settings thì 403; `session_id` không phải UUID thì 422, UUID hợp lệ thì 200. Cả 7 test pass trong suite. Test cho `ExportForConsole` đã có từ trước (`test_console_tools.py`, `test_grpc_dataset_handler_exports_without_name_error`). |

## Finding mới (A-57 trở đi, chỉ trong delta)

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-57 | P3 | quy-ước | `app/config/runtime_override_config.py:92-95`; `.gitignore:105` | AI_CONVENTIONS §4; tác dụng phụ của file cấu hình cục bộ (audit-2 A-44) | Khi `json.dump` hoặc `os.replace` lỗi (ví dụ `PermissionError` trên Windows lúc file đích đang mở), `var/runtime_settings.json.tmp` bị bỏ lại. File `.tmp` không có trong `.gitignore`, chỉ có `var/runtime_settings.json`, nên sẽ hiện thành file untracked ở `git status`. Tên tệp tạm cố định cũng dễ va nhau nếu sau này console chạy nhiều worker. | Dùng `try/finally` để xoá tệp tạm khi lỗi, hoặc tạo bằng `tempfile.NamedTemporaryFile(dir=..., delete=False)`. Thêm `var/*.tmp` vào `.gitignore`. | Verified (lượt 5) | `runtime_override_config.py:93-99`, `.gitignore:106` |
| A-58 | P2 | đúng-sai | `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx:320-329`; `app/core/console/services/tools_service.py:418`, `:455`; `app/core/forecast/services/forecast_service.py:90-91` | `ai/DESIGN.md` Hallmark 2 (không báo sai trạng thái) | Nhãn nguồn dữ liệu mới và `model_version` dựa trên `training_data.is_fallback`. Nhưng `load_lakehouse_dataset` trả **dataset đã cache của lần nạp đầu** bất kể `area_id` (`forecast_service.py:90-91`), trong khi 24 giá trị dự báo lấy từ `get_projected_occupancy_ratio_detail` theo từng giờ, mỗi giờ có `is_fallback` riêng (`:160-195`). Ví dụ: lần chạy đầu cho bãi A có dữ liệu thật, lần sau chọn bãi B chưa có dữ liệu. Khi đó cả 24 giờ của B đều là baseline, nhưng UI vẫn ghi "Dữ liệu thật từ Gold lake" và `profile-7x24`. Lỗi lệch khoá bãi đã ghi ở bug-028 làm ca này dễ xảy ra hơn. | Tính `is_fallback` cho stage3 từ chính các `detail` đã dùng (ví dụ `any(d["is_fallback"] for d in details)`, hoặc đếm số giờ dùng baseline). Có thể trả thêm `data_source` để UI hiện. Thêm test: hai `area_id` liên tiếp, một có dữ liệu và một không có. | Verified (lượt 5) | `tools_service.py` simulate_forecast (force_reload + is_fallback theo giờ) |
| A-59 | P3 | test | `test/test_console_tools.py:300-313` | Convention-audit §3.4 (assertion phải chứng minh đúng điều cần chứng minh) | `assertNotEqual(63, local_llm_threads)` vẫn pass khi rollback hỏng mà giá trị cũ khác 63 theo cách khác. Test không phủ việc khôi phục `llm_provider` hay nhánh preset. Không có test nào chạy `persist_runtime_overrides` thật tới `os.replace` (chỉ có mock). | Lưu `before_threads` và `before_provider` rồi `assertEqual` cả hai. Thêm một ca preset kèm lỗi ghi. Thêm một test `persist_runtime_overrides` trên thư mục tạm, kiểm file sau khi ghi đúng JSON và không còn `.tmp`. | Verified (lượt 5) | `test_console_tools.py` test rollback mới |
| A-60 | P3 | tài-liệu | `docs/projects/issues/10-2026/ISSUE-007-copilot-rag-heldout-dataset/issue.md` (FAIL NAMING) | `docs/check_naming.py` (NAMING_CONVENTIONS, mã hồ sơ không trùng) | FAIL duy nhất của máy quét. Thư mục cũ `ISSUE-007-console-tools-and-knowledge-management/` đã xoá ở working tree và hồ sơ chuyển sang `ISSUE-011-…` (untracked). Nhưng `check_naming.py:140` đọc `git ls-files`, nên vẫn thấy file cũ trong index. Các file này nằm ngoài danh sách được giao, không tính vào kết luận của delta. | Khi stage thì stage cả việc xoá (`git rm --cached` hoặc `git add` đúng đường dẫn cũ) lẫn thư mục `ISSUE-011-…`, rồi chạy lại máy quét. | Deferred: ngoài phạm vi, rename ISSUE-007 → ISSUE-011 stage ở commit riêng | — |

### Theo loại (Open + Reopened trong delta lượt này)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| đúng-sai | 0 | 0 | 2 (A-40 Reopened, A-58) | 0 |
| hợp-đồng | 0 | 0 | 1 (A-11/12 Reopened) | 0 |
| test | 0 | 0 | 0 | 1 (A-59) |
| quy-ước | 0 | 0 | 0 | 1 (A-57) |
| tài-liệu | 0 | 0 | 0 | 1 (A-60, ngoài danh sách giao) |
| **Tổng** | **0** | **0** | **3** | **3** |

Verified lượt này: A-53, A-25. Các finding khác của audit-3 (Deferred, A-22 chờ quyết, bug-028, bug-029) không soát lại và không nêu lại ở đây.

## WARN đã xét

| WARN | Kết luận | Lý do |
|---|---|---|
| `FE-DEFAULT-EXPORT frontend/packages/client/.../PublicLayout.tsx:22`, `.../PaymentModal.tsx:286` | Ngoài phạm vi | Thuộc repo `frontend/`, không thuộc delta `ai/` (đã xét ở audit-3). |

## Bug đã mở

Không mở, theo chỉ đạo của người điều phối. A-40 (model chọn ở Settings bị bỏ qua khi provider là `local`) và A-58 (nhãn "dữ liệu thật" sai) là lỗi chạy sai. Nếu người dùng muốn tách hồ sơ thì nên mở `bug-NNN` ở `ai/docs/projects/bugs/`. A-58 nên link tới bug-028.

## Ngoài phạm vi (nợ cũ nhìn thấy)

- `app/core/console/services/tools_service.py:388-389`: đọc `lgbm.get("X")`/`lgbm.get("y")`, trong khi reader trả `features`/`targets` (`parquet_lake_reader.py:618-620`). Vì vậy `stage2_features.total_samples` luôn bằng 0 và `sample_rows` luôn rỗng. Dòng này không có trong delta, nhưng cùng loại lệch khoá với A-11/12, nên sửa chung một lượt.
- `app/infra/llm/llama_server_manager.py:71`, `:77` và `app/infra/monitoring/ai_logger.py:113`, `:147` vẫn viết cứng `Qwen3.5-4B-Q4_K_M`, không dùng hằng của A-40.

## Cần người dùng quyết

Chặng đã quá 3 vòng. Còn 3 P2: A-11/12 (đọc sai khoá `total_records`), A-40 (nhánh GGUF bỏ qua `llm_model`) và A-58 (nhãn nguồn dữ liệu). Lựa chọn:
- **A.** Cho fixer sửa thêm một lượt. A-11/12 chỉ cần sửa một dòng kèm một assert. A-58 cần tính lại `is_fallback` và thêm một test. A-40 cần tách tên model cấu hình với tên model đang chạy. Sau đó auditor soát delta.
- **B.** Giữ `Deferred` như quyết định ở audit-3, chuyển các mô tả mới vào tiêu chí chưa tick của ISSUE-019.
- **C.** Sửa A-11/12 (nhỏ), để A-40 và A-58 Deferred hoặc tách thành bug.

## Soát lại

| Lần | Ngày | Tree | Finding đã soát | Kết quả |
|---|---|---|---|---|
| 4 | 2026-10-25 | `9c1aa479ebd4b7e5858ff16d13a13a37bd4a358a` (index tại HEAD `d55ac7c`, chưa stage gì; delta là `git diff HEAD` của 10 file được giao) | A-53, A-11/12, A-40, A-25 và hunk fixer chạm | A-53, A-25 Verified. A-11/12, A-40 Reopened (lần 1). Mới: A-57 (P3), A-58 (P2), A-59 (P3), A-60 (P3, ngoài danh sách). Còn 3 P2 → ⛔ chờ người dùng quyết |
| 5 | 2026-10-26 | `9c1aa479ebd4b7e5858ff16d13a13a37bd4a358a` (index vẫn chưa stage gì, delta vẫn là `git diff HEAD`. Chỉ soát những gì fixer đổi sau lượt 4) | A-11/12, A-40, A-57, A-58, A-59 | A-11/12, A-57, A-58, A-59 Verified. A-60 Deferred (ngoài phạm vi). **A-40 Reopened lần 2** → ⛔ hỏi người dùng ngay |
| 6 | 2026-10-26 | `9c1aa479ebd4b7e5858ff16d13a13a37bd4a358a` (chưa stage; chỉ soát hunk A-40: i18n `llmModel`/`configuredModel`, `ChatStudioHeader.tsx`, `test_llm_factory.py`) | A-40 | A-40 Verified. Mới: A-61 (P3). Không còn P0–P2 mở → ✅ |

## Lượt 5: soát lại sau hướng A (2026-10-26)

Kiểm lại: `unittest discover -s test` cho 562 OK (34 skip). mtime của `var/runtime_settings.json` không đổi (`2026-10-25 22:31:33.544`), và không có `.tmp`. `npx tsc --noEmit` PASS. `check_diff.py --repo ai` cho 1 FAIL (A-60) và 2 WARN `frontend/`. Vitest, browser và llama-server thật chưa chạy.

| # | Mức | Loại | Trạng thái fixer | Trạng thái lượt 5 | Bằng chứng / lý do |
|---|---|---|---|---|---|
| A-11/12 | P2 | hợp-đồng | Fixed | **Verified** | `tools_service.py` đọc `total_records` và đọc `lightgbm_dataset.features`/`targets`, khớp `parquet_lake_reader.py:612`, `:618-620`. Thứ tự cột của `feat` (`dow, hour, is_wk, slots, …`) khớp cách `sample_rows` đọc. Test assert `total_records > 0` và kiểm `total_samples` khớp với `sample_rows`. Nợ cũ `total_samples=0` cũng được sửa luôn. |
| A-58 | P2 | đúng-sai | Fixed | **Verified** | `load_lakehouse_dataset(area_id=area_id, force_reload=True)` không còn trả dataset của bãi khác. Stage3 giờ đặt `is_fallback = cờ dataset OR is_fallback của từng giờ`. Chỉ một giờ dùng baseline là nhãn đã chuyển sang "Baseline", nên không còn báo "Dữ liệu thật" sai. Test kiểm ca bãi không có trong lake (`is_fallback` là True, `model_version` khớp). Chưa có ca hai bãi liên tiếp, nhưng giờ dataset được nạp lại mỗi lần gọi nên ca đó không còn đường sai. Ghi chú: `force_reload` đọc lại Parquet ở mỗi lần bấm mô phỏng. Đây là thao tác thủ công trong console, nên chấp nhận được, không tính là finding. |
| A-57 | P3 | quy-ước | Fixed | **Verified** | `persist_runtime_overrides` xoá `.tmp` trong `finally` (`runtime_override_config.py:93-99`). Khi thành công thì `os.replace` đã chuyển tệp tạm đi, nên `exists` là False. `.gitignore:106` thêm `var/runtime_settings.json.tmp`. |
| A-59 | P3 | test | Fixed | **Verified** | Test patch chính `os.replace` để ném `PermissionError` (đi qua đường ghi thật). Test kiểm toàn bộ snapshot, gồm `llm_provider` sau ca đổi `local` và ca preset `cpu_eco`, rồi kiểm không còn `.tmp`. |
| A-40 | P2 | đúng-sai | Fixed | **Reopened (lần 2)** | Đã đạt: model gửi đi giờ lấy từ `llm_model` đã lọc (`llm_config.py:54-61`). Nhánh rơi sang Ollama dùng đúng model người dùng chọn. Chỉ khi llama-server trả health OK thì factory mới đổi `self.model` sang tên GGUF (`llm_factory.py:116`). GET settings trả `llm_model` cấu hình, nên ô nhập ở Settings không còn bị ghi đè. Nhãn ở Settings là "Model đang cấu hình" (`vi.ts:1199`, `en.ts:1220`), đúng nghĩa. **Còn sai đúng triệu chứng gốc của A-40 ở audit-2:** `system_check` (`tools_service.py:225`) vẫn trả `active_model_name`, tức `llm_model`. UI hiển thị giá trị đó như model đang dùng ở header của ChatStudio (`ChatStudio.tsx:34`, `:386` → `ChatStudioHeader.tsx:47`) và ở mục "Model LLM" của trang Tools (`SystemSection.tsx:38`). Khi `provider=local` và llama-server đang chạy file GGUF, chat thật dùng Qwen3.5-4B nhưng header báo `qwen2.5:0.5b`. Lượt 4 chưa nêu phần này vì khi đó nhánh GGUF của `active_model_name` che mất. Không có test cho `local_gguf_model_name` hay cho nhánh llama alive. Cách sửa gợi ý (rẻ nhất trước): (a) `system_check` trả thêm `llm_model_running`. Khi `provider=local` và llama health OK thì giá trị là `local_gguf_model_name`, còn lại là `llm_model`, và header dùng trường này. Hoặc (b) đổi nhãn ở header và SystemSection thành "Model cấu hình". |

### Theo loại (Open + Reopened sau lượt 5)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| đúng-sai | 0 | 0 | 1 (A-40, Reopened lần 2) | 0 |
| tài-liệu | 0 | 0 | 0 | 1 (A-60, Deferred, ngoài phạm vi: sẽ hết khi rename ISSUE-007 → ISSUE-011 được stage ở commit riêng) |

### Cần người dùng quyết (lượt 5)

A-40 bị Reopened lần thứ hai. Theo convention-audit §5, auditor dừng và hỏi người dùng, không mở thêm lượt sửa nào. Lựa chọn:
- **A.** Sửa theo (a) hoặc (b) ở trên. Cả hai đều nhỏ và chỉ chạm hiển thị. Sau đó auditor soát lại đúng hunk đó.
- **B.** Nhận A-40 là `Deferred`, hạ xuống P3 (chỉ còn sai nhãn hiển thị khi llama-server đang chạy, model gửi đi đã đúng), theo dõi ở ISSUE-019. Khi đó Kết luận có thể chuyển ✅.

## Lượt 6: A-40 theo hướng A, cách đổi nhãn (2026-10-26)

Kiểm lại: `unittest discover -s test` cho 563 OK (34 skip). Riêng `test.test_llm_factory` OK. mtime của `var/runtime_settings.json` không đổi. `npx tsc --noEmit` PASS. `check_diff.py --repo ai` cho 275 file, 1 FAIL (A-60), 2 WARN `frontend/`. Vitest 93/93 theo báo cáo của fixer; auditor không chạy.

| # | Mức | Loại | Trạng thái fixer | Trạng thái lượt 6 | Bằng chứng / lý do |
|---|---|---|---|---|---|
| A-40 | P2 | đúng-sai | Fixed | **Verified** | Nhãn `t.tools.llmModel` thành "Model LLM (cấu hình)" / "LLM model (configured)". Nơi dùng duy nhất là `SystemSection.tsx:38`, nên không có chỗ nào khác bị đổi nghĩa. Badge ở `ChatStudioHeader.tsx:44` có `title` và `aria-label` lấy từ `t.copilot.configuredModel(model)`, có ở cả `vi.ts` lẫn `en.ts`, câu chữ nói rõ khi llama-server chạy thì dùng GGUF. Trang Settings đã ghi "Model đang cấu hình" từ trước. Như vậy không còn chỗ nào trình bày `llm_model` như model đang chạy. Test `test_ten_model_cau_hinh_va_ten_gguf_tach_nhau` kiểm ba ca: `local` có file GGUF (giữ `llm_model`, `local_gguf_model_name` là tên file), `ollama` với tên OpenAI (ép về mặc định, không có GGUF) và `openai` (giữ nguyên). Còn lại là khoảng hở chấp nhận được: header không cho biết model thật khi llama-server đang chạy. Đây là giới hạn đã nói rõ trên UI, không còn là báo sai. |

### Finding mới lượt 6

| # | Mức | Loại | `file:line` | Luật bị vi phạm | Mô tả | Cách sửa đề xuất | Trạng thái | Đã sửa |
|---|---|---|---|---|---|---|---|---|
| A-61 | P3 | quy-ước | `ui/src/pages/Copilot/components/ChatStudio/ChatStudioHeader.tsx:44` | `ai/ui/DESIGN.md` a11y; ARIA 1.2 (không đặt tên cho phần tử `generic`) | `aria-label` gắn trên `<div>` không có `role`. Nhiều trình đọc màn hình bỏ qua tên của phần tử `generic`, nên câu giải thích "model cấu hình" có thể không được đọc. `title` chỉ hiện khi rê chuột. | Thêm `role="status"` hoặc `role="img"` cho badge, hoặc đặt câu giải thích vào một `<span>` ẩn trực quan (lớp visually-hidden có sẵn, nếu có). | Open | |

### Theo loại (Open + Reopened sau lượt 6)

| Loại | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| quy-ước | 0 | 0 | 0 | 1 (A-61) |
| tài-liệu | 0 | 0 | 0 | 1 (A-60, Deferred, ngoài phạm vi) |


## Sửa sau lượt 6 (fixer)

| # | Đã sửa | Bằng chứng |
|---|---|---|
| A-61 | Bỏ `aria-label` trên `div`; thêm span `visually-hidden` chứa câu giải thích, tên model và icon đặt `aria-hidden` để không đọc lặp. | `ChatStudioHeader.tsx` (modelBadge); tsc PASS, vitest Copilot 22/22 |
