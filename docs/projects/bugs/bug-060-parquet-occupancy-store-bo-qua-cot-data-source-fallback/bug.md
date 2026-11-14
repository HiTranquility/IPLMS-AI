# 🐛 bug-060: `ParquetOccupancyStore` bỏ qua cột `data_source='synthetic_fallback'` từ `analytic` khiến dữ liệu giả lập bị nhận nhầm là lịch sử thật

> **Đích:** `docs/projects/bugs/bug-060-parquet-occupancy-store-bo-qua-cot-data-source-fallback/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** |  |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** | 2026-11-14 |
| **Ngày báo** | 2026-11-14 |
| **Người báo** | Antigravity, khi khép kín hợp đồng nguồn dữ liệu giữa `analytic` (`bug-004`) và `ai` cùng @HiTranquility (2026-11-14) |
| **Môi trường** | `ai/` (`develop` `419666e`) |

## Hành vi thực tế

Tại `app/infra/datalake/parquet_occupancy_store.py:326`, `_normalize_records` chỉ kiểm `bool(row.get("is_fallback", False))` mà bỏ qua cột `data_source` (`"synthetic_fallback"` vs `"clickhouse"`) do `ParquetLakeExporter` bên `analytic/` (`bug-004`) đóng dấu. Khi `analytic` chạy ở môi trường dev/test lúc chưa bật ClickHouse và xuất 96 dòng giả lập (`area-zone-a`…`area-basement-b1`, `data_source="synthetic_fallback"`), `ParquetOccupancyStore` trả về `is_fallback=False`, dẫn tới:
1. `ForecastService.list_lake_areas()` liệt kê các mã bãi giả lập như bãi có lịch sử thật trong hồ dữ liệu.
2. `ForecastService.load_lakehouse_dataset()` nạp các dòng giả lập vào `_telemetry_cache` và gắn nhãn `LAKEHOUSE_PARQUET` (độ tự tin `0.86–0.98`) thay vì `HEURISTIC_BASELINE` (`0.55`).

## Hành vi mong đợi

- `ParquetOccupancyStore._normalize_records` nhận diện cả cờ `is_fallback` lẫn cột `data_source` thuộc `{"synthetic_fallback", "heuristic_baseline", "fallback"}` (không phân biệt hoa/thường) là `is_fallback=True`, đồng thời giữ nguyên trường `data_source` trong bản ghi chuẩn hóa và khi ghi file qua `write_occupancy_parquet`.
- `ForecastService.list_lake_areas()` và `_telemetry_cache` loại trừ hoàn toàn các dòng `data_source="synthetic_fallback"`, trả đúng `ForecastDataSource.HEURISTIC_BASELINE` (`is_fallback=True`).

## Tái hiện

1. Ghi một bảng Parquet có `area_key="area-zone-a"`, `data_source="synthetic_fallback"` (không có cột `is_fallback`) rồi gọi `ForecastService.list_lake_areas()`: trước khi sửa trả về `[{'area_id': 'area-zone-a', 'records': 24}]` thay vì `[]` (`test/test_forecast_lake_areas.py::ForecastLakeAreaTest::test_synthetic_fallback_data_source_column_from_analytic_exporter_is_treated_as_fallback` đỏ).

## Bằng chứng

- `app/infra/datalake/parquet_occupancy_store.py:326,351-359`
- `app/core/forecast/services/forecast_service.py:102,138`
- Đối chiếu `analytic/etl/parquet_lake_exporter.py:224,335` (`analytic/bug-004`)

## Sửa / kiểm chứng

- Cập nhật `app/infra/datalake/parquet_occupancy_store.py` và `app/core/forecast/engines/parquet_lake_reader.py`: đồng bộ hai chiều giữa `data_source` và `is_fallback` khi đọc/ghi Parquet và khi sinh baseline.
- Thêm test hồi quy trong `test/test_forecast_lake_areas.py`: đỏ trước khi sửa (`FAILED (failures=1)`), xanh sau khi sửa (`Ran 8 tests — OK`); `test_parquet_lake_reader.py`, `check_core_layout.py`, `check_branch_policy.py`, `check_generated.py` đều PASS.
