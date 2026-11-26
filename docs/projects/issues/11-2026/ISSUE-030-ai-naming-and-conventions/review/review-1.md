# review-1: Kiểm chứng khắc phục naming, env config hygiene & `DESIGN.md` trong `ai/` (AUDIT-009)

> Hồ sơ cha: [ISSUE-030](../issue.md) · Audit nguồn: [AUDIT-009](../../../../audits/11-2026/AUDIT-009-naming-va-conventions-ai.md) · Quy ước: [AI_CONVENTIONS](../../../../../standards/AI_CONVENTIONS.md), [NAMING_CONVENTIONS](../../../../../../../docs/standards/NAMING_CONVENTIONS.md)

**Kết quả một dòng:** Khắc phục xong toàn bộ 4 vi phạm `os.environ`/`os.getenv` ngoài `app/config/` (A1–A4) và 7 mục naming / UI / `DESIGN.md` / link / layout gate (B1–B7); `check_core_layout` đạt `0 lệch`, `docs/check_naming.py` đạt `0 error, 0 warn` trên `4520` file, UI `typecheck` pass và Vitest `23/23` file (`113/113` test) pass, Python targeted suite `84` test pass (`4` skipped do thiếu `AI_TEST_DATABASE_URL`).

## Sơ đồ luồng kiểm soát config & naming

```mermaid
flowchart LR
  ENV[Biến môi trường .env / OS] --> CFG["app/config/ (BaseConfig + resolve_model_secret)"]
  CFG --> INFRA["app/infra/ & app/core/ (get_config)"]
  GATE["script/check_core_layout.py (env_access_violations)"] -. chặn os.environ/getenv .-> APP["app/ trừ config/, script/, grpc/generated/"]
  NAMING["docs/check_naming.py + ui/tsconfig + vitest"] -. kiểm tên file & export/type .-> REPO["DESIGN.md · docs/benchmarks/ · ui/src/"]
```

ERD, sequence diagram và class diagram không áp dụng: lượt này chỉ chuẩn hoá đọc config, tên file/kiểu dữ liệu UI, đồng bộ `DESIGN.md` và bổ sung cổng kiểm tự động; không thay đổi schema DB, RPC proto hay hợp đồng REST.

## Phạm vi đã xử lý (AUDIT-009 Nhóm A & B1–B7)

| Hạng mục | File đã sửa / thêm | Kết quả |
|---|---|---|
| A1 (`AI_EMBEDDING_OFFLINE_FALLBACK`) | [`app/config/embedding_config.py`](../../../../../../app/config/embedding_config.py), [`app/infra/embedding/embedding_client.py`](../../../../../../app/infra/embedding/embedding_client.py), [`.env.example`](../../../../../../.env.example), [`test/test_config.py`](../../../../../../test/test_config.py), [`test/test_embedding_client.py`](../../../../../../test/test_embedding_client.py) | Đọc qua `EmbeddingConfig.offline_fallback` (`bool = False`); bỏ `import os` & `os.getenv` khỏi `embedding_client.py`. |
| A2 (`DATALAKE_DIR` / `AI_DATALAKE_PATH` / `LAKE_LOCAL_FALLBACK_DIR`) | [`app/config/datalake_config.py`](../../../../../../app/config/datalake_config.py), [`app/infra/datalake/parquet_occupancy_store.py`](../../../../../../app/infra/datalake/parquet_occupancy_store.py), [`test/test_config.py`](../../../../../../test/test_config.py) | Gom `AliasChoices` vào `DatalakeConfig.legacy_lake_dir`; bỏ `import os` & `os.environ.get` khỏi `parquet_occupancy_store.py`. |
| A3 (`AI_DB_HOST_PORT`) | [`app/config/server_config.py`](../../../../../../app/config/server_config.py), [`app/infra/database/db_connection.py`](../../../../../../app/infra/database/db_connection.py), [`test/test_config.py`](../../../../../../test/test_config.py), [`test/test_db_connection_fallback.py`](../../../../../../test/test_db_connection_fallback.py) | Thêm `ServerConfig.db_host_port` (mặc định `5435`); `db_connection.py` đọc qua `get_config().server.db_host_port`. |
| A4 (`secret_env_name`) | [`app/config/console_config.py`](../../../../../../app/config/console_config.py), [`app/infra/llm/connection_probe.py`](../../../../../../app/infra/llm/connection_probe.py), [`test/test_config.py`](../../../../../../test/test_config.py) | Thêm `resolve_model_secret(secret_env_name)` tại `console_config.py`; bỏ `import os` & `os.environ.get` khỏi `connection_probe.py`. |
| B1 (CSS Module case) | [`ui/src/components/common/Ui/data-display/Table.module.css`](../../../../../../ui/src/components/common/Ui/data-display/Table.module.css) + 10 file page/component trong `ui/src/pages/` | Đổi tên `table.module.css` → `Table.module.css` qua tên trung gian trên git index + filesystem và cập nhật đủ 10 import. |
| B2 (Default export thừa) | [`ui/src/services/apiClient.ts`](../../../../../../ui/src/services/apiClient.ts) | Gỡ `export default apiClient;`, giữ named export `apiClient` & `fetchSession`. |
| B3 (`any` parameter) | [`ui/src/pages/Audit/AuditPage.tsx`](../../../../../../ui/src/pages/Audit/AuditPage.tsx) | Thay `t: any` bằng `t: Messages` nhập từ `@/i18n/vi`. |
| B4 (Benchmark filename) | [`docs/benchmarks/anpr-onnx-benchmark-report.md`](../../../../../benchmarks/anpr-onnx-benchmark-report.md), [`benchmark/benchmark_anpr_latency.py`](../../../../../../benchmark/benchmark_anpr_latency.py) | Đổi sang `lower-kebab-case` và cập nhật đường dẫn xuất báo cáo trong `benchmark_anpr_latency.py:341,349`. |
| B5 (`DESIGN.md` sync) | [`DESIGN.md`](../../../../../../DESIGN.md) | Cập nhật ngày `2026-11-26`, đủ 14 config + 8 core domain (`console`, `model_policy`), `anpr/model_loader.py`, env mới và bảng ngoại lệ naming. |
| B6 (Link tài liệu sống) | [`training/README.md`](../../../../../../training/README.md#L115), [`data/golden/plates/README.md`](../../../../../../data/golden/plates/README.md#L3) | Sửa link tới `engine.py` và `docs/ideas/09-2026/IDEA-007-vision-deep-dive-roadmap.md`. |
| B7 (Cổng env layout tự động) | [`script/check_core_layout.py`](../../../../../../script/check_core_layout.py), [`script/test_check_core_layout.py`](../../../../../../script/test_check_core_layout.py) | Thêm `env_access_violations(app_root)` chặn `os.environ`/`os.getenv` ngoài `config/`, `script/`, `api/grpc/generated/` kèm unit test. |

## Đã kiểm thế nào (sau lần sửa code cuối)

| Hạng mục | Lệnh chạy | Kết quả quan sát |
|---|---|---|
| Quét `os.environ`/`os.getenv` ngoài whitelist | `git grep -n -E "os\.(environ\|getenv)\b" -- app/ ":!app/config/" ":!app/script/" ":!app/api/grpc/generated/"` | Exit `1` (`0` kết quả khớp) |
| Kiểm tra cấu trúc core & env gate | `python -X utf8 script/check_core_layout.py --core app/core` & `python -X utf8 script/test_check_core_layout.py -v` | `check_core_layout: 0 lệch` · `Ran 6 tests in 0.468s — OK` |
| Kiểm tra naming toàn repo | `python -X utf8 docs/check_naming.py` (từ gốc `IPLMS`) | `PASS: 0 error, 0 warn` (`4520 file, 0 glob ngoại lệ`, `11 DESIGN`) |
| Kiểm tra branch, generated docs & board | `script/check_branch_policy.py --branch chore/ISSUE-030-2026-11-ai-naming-and-conventions` · `script/check_generated.py` · `script/test_board_gen.py -v` · `script/test_branch_policy.py -v` | `VERIFIED_LOCAL` · `check_generated` pass · `BoardGenTest`: 10 ok / 1 skipped (`check_drift.py`) · `BranchPolicyTests`: 19 ok |
| Đồng bộ dependencies & type hints | `..\script\audit\ai_reqs.py requirements.txt requirements-service.txt` · `..\script\audit\ai_hints.py app` | `0` lệch version, `0` thiếu ở dev · `322 / 1119` hàm thiếu hint (`B8`, giữ backlog riêng) |
| Biên dịch script benchmark | `.\.venv\Scripts\python.exe -m py_compile benchmark\benchmark_anpr_latency.py` | Exit `0` |
| Targeted Python unit tests | `.\.venv\Scripts\python.exe -m unittest test.test_config test.test_db_connection_fallback test.test_embedding_client test.test_console_model_connections test.test_datalake test.test_parquet_lake_reader test.test_logging_interceptor test.test_anpr_onnx_runtime -v` | `Ran 84 tests in 13.903s — OK (skipped=4)` (`ConnectionDatabaseTest` skip vì thiếu `AI_TEST_DATABASE_URL`) |
| AI Console UI typecheck & tests | `corepack pnpm --dir ui typecheck` · `corepack pnpm --dir ui test` | `tsc --noEmit` Exit `0` · Vitest `Test Files 23 passed (23)`, `Tests 113 passed (113)` |
| Baseline toàn bộ `test/` (trước khi sửa) | `.\.venv\Scripts\python.exe -m unittest discover -s test -t .` | `Ran 727 tests in 159.528s — FAILED (failures=3, skipped=41)` *(3 ca ANPR pre-existing fail trên máy có `data/models/best.onnx`: `test_anpr_pipeline.py:73,85` & `test_anpr_pipeline_upgrade.py:145`; không nằm trong phạm vi `ISSUE-030` và chưa chạy lại toàn bộ `discover` sau chỉnh sửa cuối)* |
| Postgres live DB & chạy lại toàn bộ ANPR suite | — | **NOT RUN** (`ConnectionDatabaseTest` cần `AI_TEST_DATABASE_URL`; `discover` đầy đủ chưa chạy lại sau sửa, mới chạy 8 module liên quan ở trên) |

## Ghi nhận ngoài phạm vi / Backlog

1. **`B8` — Type hints (`ai_hints.py`):** Hiện còn `322 / 1119` hàm trong `app/` thiếu đầy đủ type hint (`app/api`: 127/194, `app/infra`: 115/363, `app/core`: 49/412, `app/script`: 18/105, `app/config`: 5/17, `app/console_main.py`: 5/12, `app/main.py`: 2/3, `app/grpc_server.py`: 1/2). Không sửa đại trà trong `ISSUE-030` để giữ diff gọn và đúng phạm vi.
2. **Pre-existing ANPR ONNX baseline test failures:** 3 test trong `test/test_anpr_pipeline.py:73,85` và `test/test_anpr_pipeline_upgrade.py:145` chỉ patch PyTorch `_STATE` nên lỗi khi `data/models/best.onnx` tồn tại trên máy; nên tách issue riêng cho đội Vision nếu muốn mock/tách rõ nhánh ONNX vs PyTorch trong unit test.
3. **Link lịch sử trong hồ sơ đóng (`10-2026`, `KHOA_MODULE_GUIDE.md`):** Giữ nguyên theo nguyên tắc không sửa hồ sơ lịch sử trừ khi rà dọn docs riêng.
