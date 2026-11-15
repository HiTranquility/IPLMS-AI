# 🐛 bug-058: Cờ `onnx_enabled` của AI Console không có hiệu lực lúc chạy và thiếu bước xuất `best.onnx` thật

> **Đích:** `docs/projects/bugs/bug-058-anpr-onnx-toggle-va-thieu-script-export/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** |  |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | 2026-11-14 |
| **Ngày báo** | 2026-11-14 |
| **Người báo** | Antigravity, khi rà quy trình ONNX và AI Vision cùng @HiTranquility (2026-11-14) |
| **Môi trường** | Local dev & Docker image `ai/`, `develop` `d28b9e2` |

## Hành vi thực tế

1. **Gạt nút `onnx_enabled` trong AI Console không đổi engine đang chạy:** `ToolsService._apply_compute` (`app/core/console/services/tools_service.py:710-711`) cập nhật `cfg.vision.onnx_enabled` và ghi `var/runtime_settings.json`, nhưng `AnprOnnxEngine.__init__` (`app/core/vision/engines/anpr/onnx_engine.py:58-62`) chỉ đọc biến môi trường `os.environ.get("AI_ONNX_ENABLED")` đúng một lần khi khởi tạo singleton `_onnx_engine` (`app/core/vision/engines/anpr/engine.py:40-44`), đồng thời `is_using_onnx()` (`onnx_engine.py:171-173`) không kiểm lại `VisionConfig.onnx_enabled`.
2. **Thiếu bước xuất trọng số `best.onnx` thật:** Repo gitignore `*.onnx`, thư mục `data/models/` chỉ có `.gitkeep`, còn `Dockerfile` và `requirements*.txt` chưa có gói `onnx` lẫn script xuất từ `model/artifacts/bootstrap/anpr/best.pt`. Lúc chạy thật `AnprOnnxEngine` luôn rơi về PyTorch fallback, còn báo cáo `docs/benchmarks/anpr_onnx_benchmark_report.md:14` đang mang số giả lập từ `SimulatedOnnxSession` (`time.sleep(12ms)` ở `benchmark/benchmark_anpr_latency.py:63-110`) kèm link hỏng `../AI_CONVENTIONS.md`.

## Hành vi mong đợi

- `AnprOnnxEngine` đọc cấu hình qua `get_config().vision` theo `AI_CONVENTIONS.md` §4 (không đọc `os.environ` rải rác), tôn trọng tức thời `VisionConfig.onnx_enabled` khi bật/tắt nóng và nạp lười session có khóa `threading.Lock()` theo §6.
- Có script tất định `app/script/export_anpr_onnx.py` xuất `best.pt -> data/models/best.onnx` (hai lần chạy cho cùng SHA-256), được gọi sẵn trong `Dockerfile` lúc build image, và báo cáo benchmark ghi nhận số đo `onnxruntime` thật.

## Tái hiện

1. Khởi tạo `AnprOnnxEngine` với `cfg.vision.onnx_enabled = False` rồi gạt sang `True` (hoặc ngược lại từ `True` sang `False` khi đã có session): `engine.is_using_onnx()` không phản ánh giá trị `cfg.vision.onnx_enabled` (`test/test_anpr_onnx_runtime.py` đỏ 2 FAIL trước khi sửa).
2. Kiểm tra `data/models/` trên nhánh `develop`: chỉ có `.gitkeep`, log khởi động luôn in `ONNX model file not found (None). AnprOnnxEngine operates in PyTorch fallback mode.`

## Bằng chứng

- `app/core/vision/engines/anpr/onnx_engine.py:58,93,125,171-173` (đọc `os.environ` trực tiếp, không đọc `VisionConfig.onnx_enabled` trong `is_using_onnx()`).
- `Dockerfile:35-38`, `requirements.txt:13-14`, `requirements-service.txt:12-13` (thiếu `onnx` và bước xuất `best.onnx`).
- `docs/benchmarks/anpr_onnx_benchmark_report.md:3,14` (`SimulatedOnnxSession` `12.0ms` và link hỏng `../AI_CONVENTIONS.md`).

## Sửa / kiểm chứng

- `app/core/vision/engines/anpr/onnx_engine.py`: bỏ đọc `os.environ` trực tiếp và bỏ inline import; đọc `get_config().vision`, bổ sung `_try_load_session()` có `threading.Lock()` và kiểm động `_is_onnx_enabled_in_config()` trong `is_using_onnx()`.
- `app/script/export_anpr_onnx.py`, `Dockerfile`, `requirements.txt`, `requirements-service.txt`: thêm `onnx>=1.22.0,<1.23.0` (giữ tương thích `protobuf==5.29.5` của `grpcio-tools==1.71.0` và vượt sàn vá `CVE-2026-28500` CRITICAL / `CVE-2026-34445` / `CVE-2026-44512`), xuất nguyên tử `best.pt -> data/models/best.onnx` kèm chuẩn hóa metadata ONNX để giữ tính tất định.
- `benchmark/benchmark_anpr_latency.py`, `docs/benchmarks/anpr_onnx_benchmark_report.md`: sửa link `../standards/AI_CONVENTIONS.md`, ẩn đường dẫn máy cục bộ, định dạng `:.2f ms` và cập nhật báo cáo bằng phiên `Live ONNX Session: data/models/best.onnx` thật.
- Kiểm chứng tại máy:
  - Test tái hiện `test/test_anpr_onnx_runtime.py`: đỏ trước khi sửa (`FAILED (failures=2, errors=1)`), xanh sau khi sửa (`Ran 3 tests — OK`).
  - Bộ test ANPR (`test_anpr_onnx_runtime`, `test_anpr_benchmark`, `test_anpr_pipeline`, `test_anpr_pipeline_upgrade`, `test_confidence`): `41 tests OK`.
  - Tính tất định `export_anpr_onnx.py --force` chạy 2 lần liên tiếp: cùng SHA-256 `0caf105f4f91be7ee54d3b1e53ca67b708450c063862b62027cdc97c23051457`.
  - Kiểm quy ước: `script/check_core_layout.py` (0 lệch), `script/check_branch_policy.py` và `script/check_generated.py` đều PASS.
