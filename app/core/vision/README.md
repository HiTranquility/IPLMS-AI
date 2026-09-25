# core/vision — Nhận diện biển số (ANPR) + chống tráo xe

> Trạng thái (2026-09-25): **chạy thật** — YOLO `best.pt` bootstrap + EasyOCR (en, vi). Độ chính xác **chưa đo được** (bộ vàng 0/200, PROB-038). Phân loại loại xe **tắt** khi chưa có checkpoint.

## Điểm vào

| Cổng | File | Ai gọi |
|---|---|---|
| gRPC `VisionService.RecognizePlate` | `app/api/grpc/handlers/vision_handler.py` | Backend: staff check-in/verify check-out (`staff-operation.service.ts`) |
| gRPC `VisionService.VerifyVehicleMatch` | cùng handler | Backend: verify check-out |
| REST `POST /api/anpr/recognize[-many]` | `app/api/rest/routes/anpr_controller.py` | Backend fallback khi gRPC lỗi đường truyền; upload tay |

## Luồng một ảnh (RecognizePlate)

```text
vision_handler.RecognizePlate            map proto → RecognizePlateCommand, đẩy sang thread (CPU-bound)
  └─ services/anpr_service.recognize_bytes
       ├─ engines/anpr_engine.run_anpr   FAÇADE — chỉ điều phối các tầng dưới
       │    ├─ anpr/models.ensure_models_loaded   nạp YOLO + EasyOCR (lazy, khoá luồng)
       │    ├─ anpr/ocr.read_with_confidence      ① OCR CẢ ẢNH → ứng viên "full"
       │    ├─ anpr/detector.detect_plate         ② YOLO → ảnh cắt biển + điểm detector
       │    ├─ anpr/preprocess.is_valid_crop      ③ ảnh cắt ≥220×80, độ sáng ≥80?
       │    │     └─ có → anpr/ocr (ảnh cắt thô) → ứng viên "crop"
       │    ├─ anpr/preprocess.enhance_for_ocr    ④ chỉ khi ③ hỏng hoặc ①② bất đồng:
       │    │     phóng to → xám → khử nhiễu → CLAHE → làm nét → giãn tương phản → OCR → "enhanced"
       │    ├─ anpr/scoring.select_plate_candidate ⑤ chọn: đồng thuận > hình dạng > định dạng mạnh > điểm
       │    └─ trả: biển, confidence, ẢNH CẮT biển (bằng chứng), thời gian
       └─ engines/vehicle_classifier.classify_vehicle   (tuỳ chọn) CNN NetV1/NetV2 → loại xe hoặc None
```

`anti_fraud_service.verify_vehicle_match`: chỉ so **loại xe** lúc vào/ra; `similarity_score` luôn `0.0` = *chưa đo* (so ảnh ReID chưa làm). Backend tự so **biển** vì chỉ backend biết phiên gắn biển nào.

## File

| File | Việc | Sửa khi |
|---|---|---|
| `engines/anpr_engine.py` | Façade `run_anpr`, `warmup` | Đổi thứ tự các bước |
| `engines/anpr/models.py` | Nạp model; `initialized` chỉ bật khi OCR nạp được (bug-006) | Đổi cách nạp/cache |
| `engines/anpr/detector.py` | YOLO chọn box điểm cao nhất, cắt trong biên ảnh | Train lại `best.pt` |
| `engines/anpr/preprocess.py` | Ngưỡng ảnh cắt + chuỗi làm nét (hằng số có tên ở đầu file) | Chỉnh theo camera thật |
| `engines/anpr/ocr.py` | EasyOCR; điểm = trung bình trọng số độ dài; không đọc được → 0.0 | Thay OCR |
| `engines/anpr/plate_text.py` | Chuẩn hoá, hợp lệ (≤11 ký tự, ≥1 chữ cái), khoá so sánh | Thêm định dạng biển |
| `engines/anpr/scoring.py` | `confidence = detector × OCR` (không detector → OCR); chọn ứng viên | Đổi cách chấm |
| `engines/vehicle_classifier.py` | CNN phân loại xe, tắt khi thiếu checkpoint | Có checkpoint mới |
| `services/anpr_service.py` | Gói kết quả; REST mới ghi file vào `static/` | Đổi hợp đồng trả về |
| `services/anti_fraud_service.py` | So loại xe vào/ra | Làm ReID ảnh |

## Cấu hình (`app/config/vision_config.py`, prefix `AI_`)

`AI_YOLO_MODEL_PATH`, `AI_OCR_LANGUAGES=en,vi`, `AI_OCR_MODEL_STORAGE_DIR`, `AI_VISION_WARMUP_ON_START` (true = nạp xong mới mở cổng; false = mở cổng ngay, nạp nền), `AI_VEHICLE_CHECKPOINT`.

## Ảnh ANPR có vào datalake / bộ dữ liệu train không? Ngưỡng bao nhiêu %?

**Hiện tại: KHÔNG có ảnh nào tự đi vào datalake hay bộ train.**
- Ảnh cắt được backend lưu làm **bằng chứng phiên đỗ** (`StorageProvider`, folder `Sessions`) — không phải dữ liệu train.
- Datalake hiện chỉ chứa **phiên đỗ** cho forecast, cố ý **không** có biển số/ảnh (`app/infra/datalake/session_exporter.py`).
- Luật chọn ảnh để đưa người review **đã viết** ở `core/dataset` nhưng **chưa có code chạy thật nào gọi** (chỉ test gọi) — xem [core/dataset/README.md](../dataset/README.md). Theo luật đó: điểm **< 0.75 (75%)** → đề xuất cho người review; ≥ 75% không chọn (trừ mẫu kiểm ngẫu nhiên). Dự đoán máy **không bao giờ** tự thành nhãn.

## Test

`test/test_anpr_pipeline.py` (ảnh bằng chứng), `test_confidence.py` (điểm, chọn ứng viên, detector), `test_plate_text.py`, `test_anpr_model_loading.py` (bug-006), `test_vision_mapper.py`. Đo trên container: `python app/script/benchmark_vision_grpc.py`; đo độ chính xác: `training/eval_plates.py` (cần bộ vàng).
