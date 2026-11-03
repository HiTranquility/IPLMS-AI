# 🏷️ ISSUE-022: Models & Connections trong AI Console — chặng 1: một nguồn model (sửa X2)

> **Đích:** `docs/projects/issues/10-2026/ISSUE-022-models-connections-mot-nguon-model/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress — chặng 1 (X2) PR #119; chặng 2 code + test xong (cả DB thật), cùng PR #119; chặng 3–4 chưa làm |
| **Người nhận** | @HiTranquility |
| **Hạn** | |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** | |
| **Người phụ trách** | HiTranquility (Claude soạn và code chặng 1) |
| **Phạm vi** | `ai` (chặng 1–3); chặng 4 chạm thêm `backend` + `frontend/platform` |

> Bắt nguồn từ: IPLMS [REQ-020](../../../../../../docs/requirements/10-2026/REQ-020-models-connections-ai-console.md) · IPLMS [ADR-0061](../../../../../../docs/projects/adrs/10-2026/0061-models-connections-o-ai-console-giu-kho-o-ai-db.md)

## Mục tiêu

Đưa việc quản lý model LLM theo tác vụ về một trang "Models & Connections" trong AI Console, đúng ADR-0061. **Chặng 1** sửa lỗi X2 của REQ-020: trang Settings lưu `llm_provider`/`llm_model` và báo thành công, nhưng khi đã có revision ACTIVE thì inference vẫn dùng revision (`app/infra/llm/llm_factory.py:58`). Thêm vào đó, console hiển thị model env như thể đang chạy.

## Tiêu chí chấp nhận

### Chặng 1 — một nguồn model (X2)

- [x] Settings không còn nhận `llm_provider`/`llm_model`. API trả 422 thay vì `extra="ignore"` nuốt im (`app/api/rest/routes/console_tools_controller.py` `ComputeSettingsIn.reject_model_fields`). Service cũng từ chối (`app/core/console/services/tools_service.py` `_apply_compute`).
- [x] Preset phần cứng không còn lặng lẽ chuyển provider sang `local`.
- [x] File `var/runtime_settings.json` cũ còn hai khoá này bị bỏ qua; env là dự phòng (`app/config/runtime_override_config.py` `_FIELDS`).
- [x] `GET /tools/settings` trả `models[]` theo tác vụ: `source` = `profile` (kèm `revision`), `env` hoặc `unknown` khi không đọc được `ai-db`. Model dựng bằng `LlmFactory` giống `for_task`, nên khớp inference (`tools_service._effective_models`).
- [x] `GET /tools/system` → `llm_model` là model Copilot inference dùng thật (thẻ "Copilot đang dùng" ở Copilot Lab và trang Công cụ đọc trường này).
- [x] UI Settings: bỏ ô chọn provider/model và danh sách model dò được; thêm bảng chỉ-đọc "Model đang chạy theo tác vụ" (VI/EN).
- [ ] Kiểm trên stack dev thật (browser): kích hoạt một revision ở platform → Settings và Copilot Lab hiện đúng revision đó — **chưa chạy**, xem Bàn giao.

### Chặng 2 — Connections

- [x] ERD + thuộc tính + index chốt trước khi viết DDL: [schema-chang-2-connections.md](phase/schema-chang-2-connections.md) — ✅ @HiTranquility 2026-10-28, nguyên đề xuất Q-A…Q-F.
- [x] Bảng `ai_model_connections` + `uq_ai_model_connections_active_name` trong `ModelPolicyStore.ensure_schema()`; store tạo/sửa (bản mới + `replaces_id`)/tắt/ghi kết quả thử (`app/infra/database/model_policy_store.py`).
- [x] API `GET/POST /api/models/connections`, `POST …/{id}/disable`, `POST …/{id}/test`, `POST …/test` (bản nháp, không ghi `ai-db`) — `app/api/rest/routes/console_model_controller.py`; xem `ai:metrics:read`, ghi/thử `ai:model:propose`; mỗi thao tác ghi `audit_event` (`model.connection_create|disable|test`).
- [x] Chống SSRF: allowlist `AI_CONSOLE_MODEL_CONNECTION_HOSTS`, luôn chặn link-local/metadata sau khi phân giải DNS, nối thẳng IP đã kiểm, không theo redirect, đọc ≤ 1 MiB (`app/core/console/guardrails/model_endpoint.py`, `app/infra/llm/connection_probe.py`); timeout 10 s; 10 lần/phút/thành viên → 429 (`app/core/console/engines/rate_limiter.py`).
- [x] Secret: chỉ lưu tên biến, phải có tiền tố `AI_LLM_KEY_` hoặc nằm trong `AI_CONSOLE_MODEL_SECRET_NAMES` (Q-B).
- [x] Test DB thật (`ConnectionDatabaseTest`, 4 test) PASS trên container `pgvector/pgvector:pg16` tạm, kèm `test_model_policy` (dùng chung `ensure_schema`) — 41 test PASS.
- [ ] UI trang Models & Connections — chưa làm (gộp vào chặng 3 cùng revision).

### Chặng 3–4 (chưa làm)

- [ ] **Chặng 3 — Revision trong console:** trang Models & Connections tạo/thử/so sánh/quay về; quyền `ai:model:activate` (cấp `ai_lead`, step-up); bốn mắt cho `copilot_answer` (ADR-0061 §3, §5).
- [ ] **Chặng 4 — Platform chỉ đọc:** cờ console quản lý model; bật thì API ghi backend trả 409, platform hiện model đang dùng + link sang console (ADR-0061 §4).

## Kế hoạch

1. Chặng 1 (đã làm) → kiểm: `python -m unittest test.test_console_tools test.test_console_settings_http test.test_llm_factory`; `npx tsc --noEmit`, `npx vitest run`, `npx vite build` trong `ui/`.
2. Chặng 2 → kiểm: test DB thật cho bảng connection, test SSRF/rate limit.
3. Chặng 3 → kiểm: ma trận quyền (`test/test_console_access.py`), test bốn mắt và step-up.
4. Chặng 4 → kiểm: test hai chế độ cờ ở backend; browser platform + console.

## Kiểm chứng chặng 1 (2026-10-27)

| Lệnh | Kết quả |
|---|---|
| `python -m unittest test.test_console_tools test.test_console_settings_http test.test_llm_factory` | PASS — 48 test (4 test mới, 2 test sửa theo hành vi mới) |
| `python -m unittest discover -s test -t .` | 600 test, **2 FAIL có sẵn trên `develop`** (đã kiểm bằng bản gốc của 5 file đổi), ghi ở [bug-047](../../../bugs/bug-047-rag-khong-ngu-canh-van-goi-llm/bug.md) (nhánh chore) |
| `ui`: `npx tsc --noEmit` | PASS |
| `ui`: `npx vitest run` | PASS — 104 test (1 test mới cho bảng model) |
| `ui`: `npx vite build` | PASS |
| Browser trên stack dev | NOT RUN — console cần Google OIDC + TOTP và phải chạy từ thư mục gốc, không từ worktree |

## Kiểm chứng chặng 2 (2026-10-28)

| Lệnh | Kết quả |
|---|---|
| `python -m unittest test.test_console_model_connections` | PASS — 32 test, 4 skip (test DB thật thiếu `AI_TEST_DATABASE_URL`) |
| `python -m unittest discover -s test -t .` | 638 test, **2 FAIL có sẵn** (bug-047), 40 skip |
| `python script/check_core_layout.py` | 0 lệch (thêm slot `console/guardrails/`) |
| `ui`: `npx tsc --noEmit`, `npx vitest run src/pages/Audit` | PASS (mã audit mới có trong `auditActionCodes.json` + i18n VI/EN) |
| `AI_TEST_DATABASE_URL=<pg16 tạm> python -m unittest test.test_console_model_connections test.test_model_policy` | PASS — 41 test, 0 skip |

## Bàn giao

- **Đổi hành vi cần biết:** máy nào đang dùng Settings để chọn `ollama`/`local` hoặc tên model thì sau khi merge sẽ về giá trị env (`AI_LLM_PROVIDER`, `AI_LLM_MODEL`). Muốn đổi model thì tạo và kích hoạt revision (tạm thời ở trang Hồ sơ model AI của platform cho tới chặng 3).
- **Dead code có sẵn, không đụng:** khoá i18n `settings.providerLocal` đã không được dùng từ trước.
- **Làm tiếp từ:** chặng 3 (revision gắn `connection_id` + trang Models & Connections).
- **Cấu hình mới:** `AI_CONSOLE_MODEL_CONNECTION_HOSTS` rỗng = chặn hết; máy dev cần đặt (mẫu ở `.env.example`).

## Hồ sơ liên quan

- IPLMS [REQ-020](../../../../../../docs/requirements/10-2026/REQ-020-models-connections-ai-console.md) (X2, F1–F10) · IPLMS [ADR-0061](../../../../../../docs/projects/adrs/10-2026/0061-models-connections-o-ai-console-giu-kho-o-ai-db.md)
- IPLMS ISSUE-016 (profile store gốc) · [ISSUE-019](../ISSUE-019-console-settings-va-don-audit-006/issue.md) (Settings console)
- [bug-047](../../../bugs/bug-047-rag-khong-ngu-canh-van-goi-llm/bug.md) — lỗi có sẵn, phát hiện khi chạy suite
