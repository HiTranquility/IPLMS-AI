# core/forecast — Dự báo lấp đầy + đề xuất giá động

> Trạng thái (2026-09-25): **phục vụ đang TẮT có chủ đích.** Cả hai RPC trả `UNIMPLEMENTED` (backend → HTTP 501, UI hiện "Chưa có model"). Phần dữ liệu + huấn luyện offline có thật ở `training/forecast/`, chưa có model nào vượt quality gate (PROB-039).

## Điểm vào (phục vụ)

```text
grpc ForecastService.GetOccupancyForecast / GetDynamicTariffRecommendation
  └─ app/api/grpc/handlers/forecast_handler.py   map proto → query, đẩy sang thread
       └─ services/forecast_service.py            raise FeatureNotImplementedError
            → interceptor → UNIMPLEMENTED → backend NotImplementedException (501)
```

Vì sao tắt: bản cũ trả dãy số công thức `min(0.95, 0.40 + (i*0.08) % 0.60)`, `confidence 0.89` cứng và hệ số giá `1.15` cho mọi bãi — hệ số giá nhân vào tiền khách trả. Engine sinh số đó (`engines/occupancy_model.py`) **đã xoá 2026-09-25**; `engines/` hiện trống có chủ đích.

## Luồng dữ liệu + huấn luyện (offline, KHÔNG chạy trong request)

```text
1. app/script/export_parking_sessions.py
     └─ app/infra/datalake/session_exporter.py    PostgreSQL nghiệp vụ → JSONL bất biến + manifest/checksum
          (chỉ khoảng thời gian đỗ + bãi + capacity; KHÔNG user/xe/biển/ảnh), watermark tăng dần
2. app/infra/datalake/occupancy_reader.py          đọc JSONL, khử trùng (session_id+updated_at),
                                                   chia vào slot 30 phút → occupancy
3. python -m training.forecast.run_experiment --as-of <thời điểm>
     ├─ snapshot.py        dựng dataset có phiên bản từ export thô
     ├─ dataset.py         chuẩn hoá lưới thời gian; slot THIẾU vẫn là thiếu (không bịa 0)
     ├─ features.py        đặc trưng đúng thời điểm (không rò tương lai) + chia theo thời gian
     ├─ build_features.py  ghi các split đặc trưng bất biến
     ├─ baselines.py       persistence / theo mùa — mốc phải thắng
     ├─ backtest.py        đánh giá baseline trên export
     ├─ ridge_model.py     ứng viên ridge nhỏ, kiểm tra được
     └─ train.py           huấn luyện ứng viên offline; KHÔNG promote, KHÔNG serve
```

## Khi nào bật lại phục vụ

Theo PROB-039 (Option C): model phải **thắng baseline** trên backtest theo thời gian + chạy shadow; tariff chỉ nối vào forecast sau khi có policy được duyệt. Lúc đó mới dựng `engines/` (dùng lại `training/forecast/features.py`, nạp artifact, predict) và bỏ `FeatureNotImplementedError`.

## Kiểm tra dữ liệu

`python -m app.script.export_parking_sessions --status` · `python training/readiness.py` (chỉ đọc, báo thiếu dữ liệu) · test: `test/test_datalake.py`, `test/test_forecast_training.py`.
