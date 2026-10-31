# 🐛 bug-028: Forecast Simulator luôn chạy baseline vì id bãi trên UI lệch `area_key` của Gold lake

> **Đích:** `docs/projects/bugs/bug-028-forecast-id-bai-lech-area-key/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🟢 Fixed (chờ merge) / 🟠 sai số liệu hiển thị |
| **Người báo** | Claude Code, phát hiện khi soạn lộ trình console (SUGGESTION-006 F-1) cùng đợt [ISSUE-019](../../issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md) |
| **Ngày báo** | 2026-10-25 |
| **Môi trường** | local, `develop` + WIP ngày 2026-10-25 |
| **Người nhận** | Claude Code (nhánh `bugfix/bug-028-2026-10-forecast-area-key-and-source-label`) |
| **Hạn** | — |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | — |

## Hành vi thực tế

Chọn bất kỳ bãi nào ở Forecast Simulator (trang Công cụ) thì service đều không tìm thấy dữ liệu, rơi vào `heuristic_baseline` và vẫn hiển thị như một dự báo từ model. Gợi ý giá động vì thế dựa trên đường cong giả cho mọi bãi.

## Hành vi mong đợi

- Danh sách bãi trên UI lấy từ cùng nguồn với dữ liệu (API liệt kê các `area_key` có trong lake), hoặc có bảng ánh xạ id được tài liệu hoá.
- Bãi chưa có dữ liệu thì UI ghi rõ "Baseline, chưa có dữ liệu", không trình bày như số của model.

## Tái hiện

1. `cd ai && python -m unittest test.test_console_tools` → log ghi: `Không tìm thấy bản ghi cho area_id 'lot_landmark_81' trong Parquet Lake directory. Kích hoạt fallback.` và `is_fallback=True`.
2. Đọc `area_key` trong Gold lake:
   ```
   python -I -c "import pyarrow.parquet as pq,glob; print({k for f in glob.glob('../analytic/var/datalake/gold/occupancy/**/*.parquet',recursive=True) for k in pq.read_table(f).column('area_key').to_pylist()})"
   ```
   → chỉ có `{'area-zone-a','area-zone-b','area-basement-b1','area-vip-c'}`.
3. So với `ui/src/constants/parkingLots.ts`: `lot_landmark_81`, `lot_vincom_center`, `lot_suburban_hub`, `lot_central_01`, `lot_west_gate`. Không có id nào trùng.

## Bằng chứng

- `ui/src/constants/parkingLots.ts:9-15`: danh sách cứng.
- `app/core/forecast/readers/parquet_lake_reader.py:167`, `:205`: nhánh fallback.
- `app/core/forecast/services/forecast_service.py:182-194`: baseline `data_source="heuristic_baseline"`.
- Gold lake: `analytic/var/datalake/gold/occupancy/year=2026/month=10/`, 3 file × 96 dòng (288 dòng, 4 khu).
- Cùng chỗ có các lỗi đi kèm (ghi ở AUDIT-006 A-11/12 và SUGGESTION-006 §5): `tools_service.py` (`simulate_forecast`) gán cứng `model_version="lightgbm-prophet-v1.4"` dù không nạp model nào; `current_occupancy_pct` lấy theo giờ đỉnh.

## Sửa / kiểm chứng

Sửa 2026-10-28, cùng đợt IPLMS [REQ-022](../../../../../docs/requirements/10-2026/REQ-022-forecast-tuong-tac-theo-vai.md) F1–F3:

- **Nguyên nhân gốc 1 — danh sách cứng:** Simulator chọn bãi từ `PARKING_LOTS`. Thêm `ForecastService.list_lake_areas()` (`app/core/forecast/services/forecast_service.py`) và `GET /tools/forecast/areas` (`app/api/rest/routes/console_tools_controller.py`); `ForecastSimulator.tsx` lấy danh sách từ endpoint này qua `useForecastAreas`, lake rỗng thì khoá nút chạy pipeline. `PARKING_LOTS` vẫn dùng cho Copilot/Ingest (không thuộc bug này).
- **Nguyên nhân gốc 2 — nhãn sai sau khi nạp (tìm thêm khi viết test):** `load_lakehouse_dataset(area_id=X)` với X không có trong lake trả bản ghi baseline, và các bản ghi đó được nạp vào cache telemetry. Lần hỏi sau cho X trả `data_source="lakehouse_parquet"`, `is_fallback=False` cho số baseline. Giờ chỉ bản ghi không phải fallback mới vào cache.
- **Nguồn số qua gRPC:** `OccupancyForecastResponse` và `TariffRecommendationResponse` thêm `data_source = 4`, `is_fallback = 5` (proto gốc, `ai/proto`, bản backend; `check_proto_sync.py` sạch). Kết quả gộp nhiều khung giờ: chỉ cần một khung baseline là cả kết quả gắn baseline.
- Nhãn Console: bỏ "PREDICTIVE ML" ở badge pipeline; "Dữ liệu thật từ Gold lake" → "Dữ liệu lịch sử từ Gold lake" (VI/EN), vì lake dev hiện là dữ liệu tổng hợp của exporter (xem dưới).

**Kiểm chứng**

- `test/test_forecast_lake_areas.py` (6 test): chạy trên mã `origin/develop` → 4 error + 2 fail (gồm `test_bai_ngoai_lake_khong_bi_gan_nhan_lake_sau_khi_nap`: `False is not true`); trên nhánh sửa → 6 pass.
- `python -m unittest discover -s test -t .`: 609 test, 2 fail `test_copilot_usage…test_no_context`, `test_rag_pipeline…test_no_context_does_not_call_llm` — cùng 2 fail có sẵn trên `origin/develop` (603 test), không liên quan forecast.
- `ui`: `tsc --noEmit` sạch; `vitest run` 22 file / 105 test pass, gồm 2 test mới ở `ForecastSimulator.test.tsx` (chọn bãi từ lake, gửi đúng `area_id`; lake rỗng thì khoá nút).
- Chưa kiểm trên browser stack dev: Docker không chạy và stack chạy từ checkout gốc, chưa có nhánh này.

**Còn lại / ghi chú**

- Gold lake dev (`analytic/var/datalake/gold/occupancy`) là 96 dòng tổng hợp do `analytic/etl/parquet_lake_exporter.py::_generate_occupancy_telemetry_fallback` sinh khi không có ClickHouse, không có cột đánh dấu. Forecast không phân biệt được, nên vẫn gắn `lakehouse_parquet`. Cần sửa ở analytic (đánh dấu hoặc không ghi bản tổng hợp vào gold).
- Bãi thật của backend dùng `area_id` UUID; lake dev chỉ có `area-zone-*`, nên trên 3 app mọi bãi hiện nhãn "Ước lượng sơ bộ" cho tới khi có dữ liệu export thật. Đó là hành vi đúng.
