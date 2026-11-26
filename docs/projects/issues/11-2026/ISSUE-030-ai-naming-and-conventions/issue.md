# 🏷️ ISSUE-030: Khắc phục các lệch naming, config env và `DESIGN.md` trong `ai/` (AUDIT-009)

> **Đích:** `docs/projects/issues/11-2026/ISSUE-030-ai-naming-and-conventions/issue.md` — ngoài cùng chỉ file này; `review/review-1.md` ghi kết quả kiểm chứng · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Done |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-11-26 |
| **Ưu tiên** | 🟡 |
| **Ngày tạo** | 2026-11-26 |
| **Ngày đóng** | 2026-11-26 |
| **Người phụ trách** | @HiTranquility |
| **Phạm vi** | IPLMS-AI (`app/config/**`, `app/infra/**`, `ui/src/**`, `benchmark/**`, `training/README.md`, `data/golden/plates/README.md`, `script/check_core_layout.py`, `DESIGN.md`, `docs/**`) |

## Mục tiêu

Khắc phục toàn bộ các điểm lệch về naming, truy cập `os.environ` ngoài `app/config/`, kiểu dữ liệu AI Console UI và tài liệu sống của repo `ai/` đã chỉ ra trong [AUDIT-009](../../../audits/11-2026/AUDIT-009-naming-va-conventions-ai.md), đồng thời bổ sung cổng kiểm tự động vào `script/check_core_layout.py`.

## Tiêu chí chấp nhận

- [x] `0` lệnh gọi `os.environ` / `os.getenv` ngoài `app/config/` và `app/script/` trong `app/` (kiểm tự động bởi `script/check_core_layout.py` + `script/test_check_core_layout.py`).
- [x] `ui/src/components/common/Ui/data-display/Table.module.css` dùng `PascalCase` trên cả git index và filesystem; `apiClient.ts` bỏ `export default` thừa; `AuditPage.tsx` bỏ `t: any`.
- [x] `docs/benchmarks/anpr-onnx-benchmark-report.md` dùng `lower-kebab-case` (cập nhật `benchmark/benchmark_anpr_latency.py`); sửa link hỏng ở `training/README.md` và `data/golden/plates/README.md`; cập nhật `DESIGN.md` khớp 14 config, 8 domain và bảng ngoại lệ.
- [x] `python -X utf8 script/check_core_layout.py --core app/core`, `python -X utf8 script/test_check_core_layout.py`, `corepack pnpm --dir ui typecheck`, `corepack pnpm --dir ui test`, `python -X utf8 ..\docs\check_naming.py`, và test Python liên quan chạy xanh (`84` pass, `4` skip thiếu `AI_TEST_DATABASE_URL`; 3 ca ANPR ONNX baseline fail giữ nguyên ngoài phạm vi).

## Kế hoạch

1. Gom toàn bộ truy cập `os.environ` về `app/config/` (`embedding_config.py`, `datalake_config.py`, `server_config.py`, `console_config.py`) → kiểm: `test_config`, `test_db_connection_fallback`, `test_embedding_client`, `test_console_model_connections`, `test_parquet_lake_reader`, `test_datalake`.
2. Chuẩn hoá naming & types bên `ui/src/` (`Table.module.css`, `apiClient.ts`, `AuditPage.tsx`) → kiểm: `tsc --noEmit` & `vitest run`.
3. Chuẩn hoá tên file benchmark, sửa link ở `training/README.md` + `data/golden/plates/README.md`, đồng bộ `DESIGN.md` và thêm kiểm tra `env_access_violations` vào `script/check_core_layout.py` → kiểm: `check_core_layout.py`, `test_check_core_layout.py`, `docs/check_naming.py`.
4. Chạy lại re-scan [AUDIT-009](../../../audits/11-2026/AUDIT-009-naming-va-conventions-ai.md) và lập `review/review-1.md`.

## Hồ sơ liên quan

- [AUDIT-009](../../../audits/11-2026/AUDIT-009-naming-va-conventions-ai.md)
- [review-1.md](review/review-1.md)
- [AI_CONVENTIONS](../../../../standards/AI_CONVENTIONS.md)
- [ISSUE-027](../ISSUE-027-core-naming-consistency/issue.md)
