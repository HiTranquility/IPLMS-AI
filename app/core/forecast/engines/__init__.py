"""Forecast Engines — CHƯA có model dự báo phục vụ.

`parquet_lake_reader.py` sinh baseline giờ, lọc và dựng ma trận train cho
forecast_service; phần đọc/ghi Parquet ở `app/infra/datalake/parquet_occupancy_store.py` (ISSUE-024).

`occupancy_model.py` (sinh tỷ lệ bằng công thức răng cưa, không đọc lịch sử) đã
bị xoá 2026-09-25: không nơi nào gọi và giữ lại chỉ là chỗ để bật lại số giả.
Engine thật được dựng khi một model vượt quality gate (PROB-039) — dùng lại
`training/forecast/features.py`, nạp artifact, predict; xem README của domain.
"""
