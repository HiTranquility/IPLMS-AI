# 🐛 bug-001: Cổng kiểm và nhãn AI sai im lặng — tiền, occupancy, baseline, loại xe

> **Đích:** `docs/projects/bugs/bug-001-cong-va-nhan-ai-sai-im-lang/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)
> Bốn lỗi cùng một kiểu: chỗ đáng lẽ chặn hoặc đánh dấu "không rõ" lại cho qua mà không báo gì. Tìm thấy trong một lượt rà code ngày 2026-10-06 và sửa cùng một commit, nên gom vào một hồ sơ. Kế hoạch tổng thể nằm ở `IPLMS PROB-045`, mục "Rà code 2026-10-06".

| | |
|---|---|
| **Trạng thái** | ✅ Fixed — unit test + chạy SQL thật trên Postgres/pgvector tạm; chưa E2E qua backend |
| **Người báo** | Claude (rà code theo yêu cầu chủ đồ án) |
| **Môi trường** | local (đọc code + unittest) |

## Hành vi thực tế

| # | Chỗ | Đã xảy ra gì |
|---|---|---|
| 1 | `app/core/knowledge_eval/engines/grader.py` `grade()` | So số tiền bằng chuỗi con: đáp án `25.000đ`, Copilot trả `125.000đ` vẫn **PASS**. Cổng publish chấm sai đúng loại lỗi nó sinh ra để chặn (con số trọng yếu sai thì phải bằng 0). |
| 2 | `app/infra/datalake/occupancy_reader.py` `load_historical_occupancy()` | Khung 30 phút không có phiên nào thì không sinh dòng, nên luôn bị coi là **thiếu**, kể cả khi export đã phủ khung đó. Bãi trống thật (0%) không bao giờ vào tập train, nên model học lệch lên cao. |
| 3 | `training/forecast/ridge_model.py` `evaluate_models()` | Baseline `seasonal_naive` lấy `lag_336`, tức tuần trước của **thời điểm dự báo**, chứ không phải của **giờ đích**, nên lệch đúng `horizon` ô. Thêm nữa, cổng train chỉ đòi ridge thắng persistence, nên candidate thua "giống tuần trước" vẫn qua. |
| 4 | `app/core/vision/engines/vehicle_classifier.py` | `load_state_dict(strict=False)`: checkpoint lệch kiến trúc vẫn nạp được, các lớp thiếu giữ trọng số ngẫu nhiên mà vẫn trả nhãn. `argmax` không có ngưỡng nên không bao giờ trả "không rõ", trong khi anti-fraud đem nhãn này đi so lúc check-out. |

## Hành vi mong đợi

1. Số trong đáp án không được dính liền chữ số khác (`25000đ` ≠ `125000đ`, `7 ngày` ≠ `17 ngày`).
2. Trong vùng export **liền mạch từ epoch**, khung không có phiên là 0%. Ngoài vùng đó, hoặc sau một lỗ hổng export, vẫn là thiếu.
3. Seasonal-naive dùng giá trị cùng khung tuần trước tính theo giờ đích. Candidate phải thắng baseline **tốt nhất** ở mọi horizon.
4. Checkpoint lệch thì tắt tầng phân loại (`vehicle_type = None`). Xác suất cao nhất dưới `AI_VEHICLE_MIN_CONFIDENCE` (mặc định 0.6) thì cũng trả `None`.

## Tái hiện

1. `grade("fact", "Phí tháng là 125.000đ", [], ["25.000đ"]).passed` → `True` (đã chạy trước khi sửa).
2. Ghi phiên 00:00–00:30 cùng manifest phủ tới 02:00. `load_historical_occupancy` trả đúng một dòng, không có khung 00:30–02:00.
3. Dòng có `last_occupancy=0.1`, `lag_336=0.1`, `target_same_slot_336=0.9`, đích 0.9: seasonal bị chấm sai 0.8 thay vì đúng 0.
4. Checkpoint chứa khoá lạ: model vẫn được đánh dấu đã nạp và trả nhãn.

## Bằng chứng

Mỗi lỗi có test đỏ trước khi sửa và xanh sau khi sửa:

- `test/test_knowledge_eval.py::GradeTest.test_fact_number_must_not_be_part_of_a_larger_number`
- `test/test_datalake.py::OccupancyHistoryReaderTest.test_empty_slots_inside_contiguous_export_coverage_are_zero`, `test_export_gap_stops_zero_filling`
- `test/test_forecast_training.py::test_seasonal_baseline_uses_target_week_and_gate_needs_best_baseline`
- `test/test_vehicle_classifier.py` (3 test)

## Sửa / kiểm chứng

1. Thêm `grader.contains_fact()`: dùng regex với lookbehind/lookahead `\d` ở hai đầu số.
2. Thêm `OccupancyHistoryReader.coverage_end()`, nối các cửa sổ `window` trong manifest export. Khung trống trước mốc đó được ghi `data_quality = observed_zero_within_export_coverage`. Manifest không có `window` thì bị bỏ qua (không chứng minh được vùng phủ).
3. Thêm đặc trưng `target_same_slot_{48,336}` theo giờ đích. Seasonal-naive dùng `target_same_slot_336`, thiếu thì rơi về persistence để mọi model chấm trên cùng tập dòng. `beats_persistence_every_horizon` → `beats_baselines_every_horizon`. Schema feature lên v2.
4. Dùng `strict=True`; lỗi lệch thì log rồi tắt tầng phân loại. Softmax dưới ngưỡng `vehicle_min_confidence` trả `None`.

Kiểm chứng: toàn bộ `python -m unittest discover -s test -t .` → 273 test OK, 8 skip (baseline trước khi sửa: 244 OK, 8 skip). Chưa chạy: train/backtest trên export thật (chưa có dữ liệu, `IPLMS ISSUE-014`), luồng check-out có checkpoint phân loại thật (chưa có checkpoint).
