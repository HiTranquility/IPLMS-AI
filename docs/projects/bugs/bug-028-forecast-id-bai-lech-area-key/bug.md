# 🐛 bug-028: Forecast Simulator luôn chạy baseline vì id bãi trên UI lệch `area_key` của Gold lake

> **Đích:** `docs/projects/bugs/bug-028-forecast-id-bai-lech-area-key/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New / 🟠 sai số liệu hiển thị, có đường vòng (đọc thẻ `is_fallback` ở API) |
| **Người báo** | Claude Code, phát hiện khi soạn lộ trình console (SUGGESTION-006 F-1) cùng đợt [ISSUE-019](../../issues/10-2026/ISSUE-019-console-settings-va-don-audit-006/issue.md) |
| **Môi trường** | local, `develop` + WIP ngày 2026-10-25 |

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

<Điền sau khi sửa. Đề xuất: thêm endpoint danh sách khu từ lake (hoặc fixture chung), UI bỏ danh sách cứng; test kiểm `is_fallback=False` khi area có dữ liệu và UI hiện thẻ nguồn dữ liệu.>
