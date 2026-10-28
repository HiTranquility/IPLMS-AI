# 🏷️ ISSUE-024: Tách I/O Parquet khỏi `forecast/engines/parquet_lake_reader.py` sang `infra/datalake/`

> **Đích:** `docs/projects/issues/10-2026/ISSUE-024-tach-io-parquet-lake-reader/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🚧 In progress — code xong và đã kiểm ở máy, chờ PR merge vào `develop` |
| **Người nhận** | @HiTranquility |
| **Hạn** |  |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** |  |
| **Người phụ trách** | HiTranquility |
| **Phạm vi** | IPLMS-AI: `app/core/forecast/`, `app/infra/datalake/`, `test/test_lakehouse_forecast_e2e.py`, ADR-0005, AI_CONVENTIONS |
| **Bắt nguồn từ** | [ISSUE-023](../ISSUE-023-khuon-domain-core/issue.md) — ngoại lệ tạm cuối cùng ở [ADR-0005](../../../adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md) mục 3 |

## Mục tiêu

`parquet_lake_reader.py` (689 dòng) trộn đọc/ghi Parquet với baseline giờ và map DTO forecast. Tách phần I/O sang `app/infra/datalake/` mà `infra/` không import `core.forecast` (AI_CONVENTIONS §1). Refactor: **hành vi ra ngoài không đổi** (API `ParquetLakeReader`, kết quả đọc, điều kiện fallback baseline).

## Tiêu chí chấp nhận

- [x] `app/infra/datalake/parquet_occupancy_store.py` (`ParquetOccupancyStore`): `_resolve_default_gold_lake_path`, `_parse_timestamp`, `read_records` (đọc file/thư mục/bytes/BytesIO), `_read_directory`, `_normalize_records`, `write_occupancy_parquet`. Chỉ import `app.core.exceptions` và `app.util.logger`; import module này không nạp `app.core.forecast.*` (đã kiểm qua `sys.modules`).
- [x] `app/core/forecast/engines/parquet_lake_reader.py` (345 dòng) giữ `read_occupancy_parquet` (quyết định fallback + lọc `area_id`), `generate_baseline_telemetry`, `filter_training_dataset`, `to_telemetry_items`; `write_occupancy_parquet` uỷ cho store. Bảng baseline giờ vẫn ở `forecast_dto.py`.
- [x] Store trả `None` (nguồn rỗng/chưa có/lỗi khi không strict) hoặc `[]` (có dòng nhưng không hợp lệ) để engine giữ đúng các nhánh fallback cũ, kể cả `fallback_on_error=False`.
- [x] Đường mặc định tới gold lake: file mới sâu hơn một cấp ít hơn nên dùng `parents[4]` thay `parents[5]`, vẫn trỏ `<IPLMS>/analytic/var/datalake/gold/occupancy`.
- [x] `python -m unittest discover -s test -t .` (`.venv`): 595 test, tập FAIL/ERROR **giống hệt** `origin/develop` 881fd24 — 2 FAIL của bug-047 + 5 ERROR do checkout mới chưa sinh stub gRPC (`compile_proto.py`), không liên quan.
- [x] `test_parquet_lake_reader`, `test_forecast_service`, `test_datalake` pass; `test_lakehouse_forecast_e2e` 8/8 pass khi bật `AI_RUN_REAL_LAKEHOUSE_TESTS=1` trên lake thật local (bản gốc cũng 8/8).
- [x] `python -X utf8 script/check_core_layout.py`: 0 lệch.
- [x] Bỏ ngoại lệ `parquet_lake_reader` khỏi ADR-0005 mục 3 và bảng "Không thuộc `core/`" của AI_CONVENTIONS.

## Kết quả

Báo cáo: [review-1](review/review-1.md).
