# 🩺 AUDIT-009: Naming, Config Hygiene & Conventions trong `ai/` vs `AI_CONVENTIONS` & `NAMING_CONVENTIONS`

> **Đích:** `docs/projects/audits/11-2026/AUDIT-009-naming-va-conventions-ai.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **ID** | AUDIT-009 |
| **Trạng thái** | ✅ Đóng (0 vi phạm còn lại ở A1–A4 & B1–B7; B8 ghi backlog) |
| **Ngày quét** | 2026-11-26 |
| **Người quét** | Antigravity AI (theo yêu cầu người dùng trong chat) |
| **Phạm vi (Scope)** | Toàn repo `ai/`: `app/**`, `ui/src/**`, `benchmark/**`, `training/**`, `data/**`, `script/**`, `DESIGN.md`, `docs/**` |
| **Quy ước đối chiếu** | [AI_CONVENTIONS](../../../standards/AI_CONVENTIONS.md) §1–§10 · [ui/DESIGN.md](../../../../ui/DESIGN.md) · [DESIGN.md](../../../../DESIGN.md) · [NAMING_CONVENTIONS](../../../../../docs/standards/NAMING_CONVENTIONS.md) C1–C5 |
| **Người/agent sẽ sửa** | @HiTranquility (Antigravity AI thực thi trên nhánh `chore/ISSUE-030-2026-11-ai-naming-and-conventions`) |
| **Tags** | `ai`, `naming`, `config`, `ui`, `docs`, `conventions` |

---

## 1. Luật gốc đang đo (Rule under audit)

> **[MUST]** đọc config qua `from app.config import get_config`. **[NEVER]** đọc `os.environ` rải rác trong engine/service. — *nguồn: `docs/standards/AI_CONVENTIONS.md §4`*
> **[MUST]** Python dùng `snake_case` cho file/hàm, `PascalCase` cho class, `UPPER_SNAKE_CASE` cho hằng và env key; slug tài liệu `lower-kebab-case`. — *nguồn: `AI_CONVENTIONS.md`, `NAMING_CONVENTIONS.md C3`*
> **[MUST]** CSS Module `<Component>.module.css` `PascalCase`; mọi component ngoài page xuất named export (`export function`/`export const`). — *nguồn: `ui/DESIGN.md`, `NAMING_CONVENTIONS.md C3`*
> **[MUST]** Đổi kiến trúc, tên được tham chiếu hoặc môi trường → cập nhật `DESIGN.md` trong cùng commit với code; ngoại lệ phải ghi bảng Phạm vi · Lý do · Điều kiện gỡ. — *nguồn: `NAMING_CONVENTIONS.md C1, C5`*

**Chuẩn vàng để noi theo:** [`app/api/grpc/mappers/vision_mapper.py`](../../../../app/api/grpc/mappers/vision_mapper.py) & [`app/config/server_config.py`](../../../../app/config/server_config.py) — *mapper đúng chuẩn 100%, config gom theo concern qua `BaseConfig`.*

## 2. Phương pháp quét (Method — tái lập được)

```powershell
# Từ thư mục ai/ (và gốc IPLMS cho check_naming.py)
python -X utf8 script/check_core_layout.py --core app/core
python -X utf8 ..\docs\check_naming.py
python -X utf8 ..\script\audit\ai_reqs.py requirements.txt requirements-service.txt
python -X utf8 ..\script\audit\ai_hints.py app
git grep -n -E "os\.(environ|getenv)\b" -- app/ ":!app/config/" ":!app/script/" ":!app/api/grpc/generated/"
```

- **Đã quét:** Toàn bộ `app/` (Python), `ui/src/` (TS/TSX/CSS), `benchmark/`, `training/`, `docs/`, `DESIGN.md`.
- **Tổng phát hiện ban đầu:** 🔴 `4` vị trí `os.environ`/`os.getenv` ngoài `app/config/` · 🟡 `9` lệch naming / UI / `DESIGN.md` / link ở tài liệu đang sống · ⚪ `5` ngoại lệ hợp lệ giữ nguyên.

## 3. Phát hiện (Findings)

### 🔴 Nhóm A — Vi phạm, PHẢI sửa

| # | `file:line` | Hiện trạng | Vì sao sai | Cách xử lý (→ đích) |
|---|---|---|---|---|
| A1 | [`app/infra/embedding/embedding_client.py:174`](../../../../app/infra/embedding/embedding_client.py#L174) | Gọi `os.getenv("AI_EMBEDDING_OFFLINE_FALLBACK", "")` trực tiếp trong `embed_texts()` | Vi phạm `AI_CONVENTIONS §4` (`os.environ`/`os.getenv` ngoài `app/config/`) | Thêm `offline_fallback: bool = False` vào [`app/config/embedding_config.py`](../../../../app/config/embedding_config.py) và đọc `self._config.offline_fallback` |
| A2 | [`app/infra/datalake/parquet_occupancy_store.py:27`](../../../../app/infra/datalake/parquet_occupancy_store.py#L27) | Gọi `os.environ.get("DATALAKE_DIR") or os.environ.get("AI_DATALAKE_PATH") or os.environ.get("LAKE_LOCAL_FALLBACK_DIR")` | Vi phạm `AI_CONVENTIONS §4` | Đưa `AliasChoices` cho 3 biến legacy vào [`app/config/datalake_config.py`](../../../../app/config/datalake_config.py) (`legacy_lake_dir`) và đọc qua `get_config().datalake` |
| A3 | [`app/infra/database/db_connection.py:55,115`](../../../../app/infra/database/db_connection.py#L55) | Gọi `os.environ.get("AI_DB_HOST_PORT", "5435")` trực tiếp | Vi phạm `AI_CONVENTIONS §4` | Thêm helper `resolve_db_host_port()` / field vào [`app/config/server_config.py`](../../../../app/config/server_config.py) để mọi truy cập env đi qua `app/config/` |
| A4 | [`app/infra/llm/connection_probe.py:106`](../../../../app/infra/llm/connection_probe.py#L106) | Gọi `os.environ.get(secret_env_name, "")` theo tên biến động của connection | Đọc `os.environ` trực tiếp trong `app/infra/` | Gom lookup qua helper `resolve_model_secret(secret_env_name)` trong [`app/config/console_config.py`](../../../../app/config/console_config.py) |

### 🟡 Nhóm B — Lệch naming / UI / tài liệu sống

| # | `file:line` | Hiện trạng | Đề xuất |
|---|---|---|---|
| B1 | `ui/src/components/common/Ui/data-display/table.module.css` | Tên CSS Module viết thường `table.module.css` (10 trang đang import), khác các component khác trong `Ui/` | Đổi qua tên trung gian sang [`Table.module.css`](../../../../ui/src/components/common/Ui/data-display/Table.module.css) và cập nhật 10 file import trong `ui/src/pages/` |
| B2 | [`ui/src/services/apiClient.ts:72`](../../../../ui/src/services/apiClient.ts#L72) | Có `export default apiClient;` dù 0 caller dùng default import | Xoá `export default apiClient;`, giữ named export chuẩn |
| B3 | [`ui/src/pages/Audit/AuditPage.tsx:20`](../../../../ui/src/pages/Audit/AuditPage.tsx#L20) | Tham số `t: any` trong `getRelativeTime` | Đổi sang kiểu chuẩn `t: Messages` từ `@/i18n/vi` |
| B4 | [`docs/benchmarks/anpr_onnx_benchmark_report.md`](../../../benchmarks/anpr-onnx-benchmark-report.md) & [`benchmark/benchmark_anpr_latency.py:341,349`](../../../../benchmark/benchmark_anpr_latency.py#L341) | File Markdown benchmark dùng `snake_case` thay vì `lower-kebab-case` | Đổi thành `anpr-onnx-benchmark-report.md` và cập nhật script sinh báo cáo |
| B5 | [`DESIGN.md:69-83`](../../../../DESIGN.md#L69) | Sơ đồ cây chỉ liệt kê 6 config và 6 domain; thiếu bảng ngoại lệ cho `AI_GUIDE.md`, `AI_USAGE.md`, `SETUP_GUIDE.md`, `USER_STORIES_AND_PRESENTATION.md` | Đồng bộ đủ 14 config, 8 domain (`+ console`, `+ model_policy`), `anpr/model_loader.py` và bảng ngoại lệ |
| B6 | [`training/README.md:115`](../../../../training/README.md#L115) & [`data/golden/plates/README.md:3`](../../../../data/golden/plates/README.md#L3) | Link cũ tới `anpr_engine.py` (đã đổi thành `engine.py`) và `SUGGESTION-007` (đã thành `IDEA-007` ở repo gốc) | Sửa đúng đường dẫn hiện hành |
| B7 | [`script/check_core_layout.py`](../../../../script/check_core_layout.py) | Chưa tự động bắt `os.environ`/`os.getenv` ngoài `app/config/` & `app/script/` | Bổ sung kiểm tra `env_access_violations()` + unit test trong `script/test_check_core_layout.py` |
| B8 | `ai_hints.py` | Đợt 1 (`ISSUE-030`): `322/1119` hàm thiếu hint · Đợt 2 ([`ISSUE-031`](../../issues/11-2026/ISSUE-031-anpr-test-isolation-and-type-hints/issue.md)): đưa `app/config` (`0/17`), `app/core` (`0/412`), `app/console_main.py` (`0/12`), `app/grpc_server.py` (`0/2`), `app/api/grpc/mappers/` & `logging_interceptor.py` về `0`; còn `213/1119` (`app/api` REST/gRPC handlers `78/194`, `app/infra: 115/363`, `app/script: 18/105`, `app/main.py: 2/3`) | Tiếp tục xử lý phần còn lại ở đợt bảo trì riêng sau khi merge `ISSUE-145` |

### ⚪ Nhóm C — HỢP LỆ (giữ nguyên, KHÔNG sửa)

| `file:line` | Chỗ | Vì sao được miễn |
|---|---|---|
| `app/api/grpc/mappers/*.py` | Toàn bộ 7 mapper (41 hàm public) | Đạt 100% quy tắc `to_*_{command,query,response,event}` / `to_answer_chunk` |
| `app/core/*/services/*.py` & `app/api/rest/routes/*_controller.py` | Toàn bộ service & REST controller | `script/check_core_layout.py` đạt `0 lệch` |
| `requirements.txt` vs `requirements-service.txt` | Dependency sets | `ai_reqs.py` báo `0` gói lệch version, `0` gói thiếu ở dev |
| `AI_GUIDE.md`, `AI_USAGE.md`, `SETUP_GUIDE.md`, `USER_STORIES_AND_PRESENTATION.md` | Tài liệu cấp gốc repo AI | Hợp đồng chấm điểm Final Project & link từ `README.md`/`BOARD.md`; ghi ngoại lệ trong `DESIGN.md` |
| `ui/src/main.tsx`, `ui/src/test/utils.tsx` | Entrypoint & test helper | Entrypoint Vite (`main.tsx`) và helper test chữ thường theo quy ước React/Vite |

## 4. Việc giao cho người/agent sửa (Remediation handoff)

1. Tạo nhánh `chore/ISSUE-030-2026-11-ai-naming-and-conventions` và hồ sơ [ISSUE-030](../../issues/11-2026/ISSUE-030-ai-naming-and-conventions/issue.md).
2. Xử lý A1–A4 (`app/config/*` + `app/infra/*`), B1–B7 (`ui/src/**`, `docs/benchmarks/`, `DESIGN.md`, `training/README.md`, `data/golden/plates/README.md`, `script/check_core_layout.py`).
3. **Verify:** chạy `check_core_layout.py`, `test_check_core_layout.py`, `docs/check_naming.py`, `unittest`, `ui typecheck` & `vitest run`.

## 5. Kiểm tra tuân thủ lại (Re-scan / Compliance check)

- **Lúc quét:** 4 vi phạm `os.environ`/`os.getenv` ngoài `app/config/` + 7 mục naming/UI/DESIGN/link (A1–A4, B1–B7) · **Sau sửa (`2026-11-26`):** `0` vi phạm còn lại ở A1–A4 và B1–B7 (chi tiết kiểm chứng tại [review-1.md](../../issues/11-2026/ISSUE-030-ai-naming-and-conventions/review/review-1.md)):
  - `git grep -n -E "os\.(environ|getenv)\b" -- app/ ":!app/config/" ":!app/script/" ":!app/api/grpc/generated/"` → Exit `1` (`0` hits)
  - `python -X utf8 script/check_core_layout.py --core app/core` → `check_core_layout: 0 lệch` · `script/test_check_core_layout.py` → `Ran 6 tests — OK`
  - `python -X utf8 ..\docs\check_naming.py` → `PASS: 0 error, 0 warn` (`4520 file, 0 glob ngoại lệ`)
  - `corepack pnpm --dir ui typecheck` → Exit `0` · `corepack pnpm --dir ui test` → `23 passed (23)`, `113 passed (113)`
  - `unittest` 8 module liên quan → `Ran 84 tests — OK (skipped=4 thiếu AI_TEST_DATABASE_URL)`; `B8` (`ai_hints.py`: `322/1119`) và 3 ca ANPR ONNX baseline pre-existing giữ ngoài phạm vi.

## 6. Liên kết (Link hai chiều)

- Sinh ra từ: Yêu cầu audit naming & conventions của chủ dự án trong chat (`2026-11-26`).
- Đẻ ra: [ISSUE-030](../../issues/11-2026/ISSUE-030-ai-naming-and-conventions/issue.md).
