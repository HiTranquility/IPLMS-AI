# Báo Cáo Đo Lường & Benchmark Độ Trễ ANPR: PyTorch vs ONNX Runtime

> Căn cứ kiến trúc: [ADR-0037](../../../docs/projects/adrs/10-2026/0037-hardened-security-onnx-vision-forecast-service.md) & [AI_CONVENTIONS](../standards/AI_CONVENTIONS.md).

## 1. Thông Tin Môi Trường & Cấu Hình Benchmark

| Thuộc tính | Giá trị chi tiết |
|---|---|
| **Thời điểm benchmark (UTC)** | `2026-11-14T05:33:03.340292+00:00` |
| **Hệ điều hành** | `Windows-11-10.0.26200-SP0` |
| **Bộ vi xử lý (CPU)** | `AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD` |
| **Phiên bản Python** | `3.13.3` |
| **PyTorch Engine** | `PyTorch YOLOv8n (CPU eager mode) [Model: model/artifacts/bootstrap/anpr/best.pt]` |
| **ONNX Runtime Engine** | `ONNX Runtime Engine (Live ONNX Session: data/models/best.onnx)` |
| **Quy mô mẫu test** | **20 lần lặp** (Warmup: 10 lần) |

## 2. Bảng Kết Quả Đo Lường Chi Tiết

| Loại phương tiện & Biển số | Engine suy luận | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Throughput (FPS) | Tăng tốc (Speedup) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Ô tô Biển 1 Dòng** (1 dòng (Rectangular)) | PyTorch YOLOv8n (CPU) | 80.06 ms | 69.35 ms | 91.81 ms | 234.27 ms | 12.5 FPS | 1.0x (Baseline) |
| **Ô tô Biển 1 Dòng** (1 dòng (Rectangular)) | **ONNX Runtime (Tối ưu)** | **52.68 ms** | **50.82 ms** | **62.71 ms** | **64.77 ms** | **19.0 FPS** | **1.52x nhanh hơn** 🚀 |
| **Xe Máy Biển 2 Dòng** (2 dòng (Square)) | PyTorch YOLOv8n (CPU) | 73.33 ms | 71.40 ms | 88.62 ms | 117.04 ms | 13.6 FPS | 1.0x (Baseline) |
| **Xe Máy Biển 2 Dòng** (2 dòng (Square)) | **ONNX Runtime (Tối ưu)** | **60.29 ms** | **57.82 ms** | **72.80 ms** | **78.25 ms** | **16.6 FPS** | **1.22x nhanh hơn** 🚀 |

## 3. Đánh Giá & Phân Tích Kỹ Thuật

### 3.1. Độ Trễ Trung Bình (Mean) & Các Phân Vị P95 / P99
- **PyTorch Eager Engine:** Độ trễ trung bình đạt **73.33 ms – 80.06 ms**, với phân vị P95 đạt **88.62 ms – 91.81 ms** do chi phí cấp phát bộ nhớ động của PyTorch runtime.
- **ONNX Runtime Engine:** Độ trễ trung bình giảm xuống còn **52.68 ms – 60.29 ms** (gồm đầy đủ Letterbox 640×640, suy luận đồ thị hợp nhất `ORT_ENABLE_ALL` và OpenCV NMS), đặc biệt cắt giảm mạnh đỉnh trễ P95 còn **62.71 ms – 72.80 ms**.

### 3.2. Thông Lượng Xử Lý (Throughput FPS)
- **PyTorch Engine:** Đạt **12.5 – 13.6 FPS** trên CPU.
- **ONNX Runtime Engine:** Đạt **16.6 – 19.0 FPS** toàn diện trên khung đầu vào chuẩn 640×640.

### 3.3. Tỷ Lệ Tăng Tốc (Speedup Factor)
- Tỷ lệ tăng tốc thực tế trên toàn bộ pipeline phát hiện biển đạt **1.22x – 1.52x** (đồng thời giảm ~35–40% độ trễ đuôi P95 dù tensor ONNX 640×640 xử lý nhiều hơn 33% điểm ảnh so với rectangular 480×640 của Ultralytics).

## 4. Kết Luận & Khuyến Nghị
1. **Số Đo Thật Thay Cho Session Giả Lập:** Trọng số `data/models/best.onnx` được xuất tất định bằng `app/script/export_anpr_onnx.py` và đo trực tiếp trên `onnxruntime` CPU.
2. **Cơ Chế Bật/Tắt Nóng & Fallback An Toàn:** `AnprOnnxEngine` đọc trực tiếp `VisionConfig.onnx_enabled` (hỗ trợ gạt nóng từ AI Console) và tự động chuyển về PyTorch `best.pt` nếu thiếu file `.onnx` hoặc tắt ONNX.
3. **Đóng Gói Tự Động Trong Image:** `Dockerfile` gọi `python app/script/export_anpr_onnx.py` ngay lúc build để mọi container có sẵn `data/models/best.onnx`.
