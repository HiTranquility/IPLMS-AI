# 🐛 bug-050: `ANPR_MAX_IMAGE_BYTES` / `ANPR_MAX_FILES_PER_REQUEST` mất khỏi `app/core/constants.py` sau khi merge, REST ANPR không import được

> **Đích:** `docs/projects/bugs/bug-050-anpr-thieu-hang-so-upload-sau-merge/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🔴 |
| **Ngày đóng** | 2026-10-31 |
| **Người báo** | Antigravity (khi đồng bộ develop trước lần chạy cuối) |
| **Ngày báo** | 2026-10-31 |
| **Môi trường** | develop `3abde8c` (origin) |

## Hành vi thực tế

- `app/api/rest/image_upload.py:4` import `ANPR_MAX_IMAGE_BYTES` và `app/api/rest/routes/anpr_controller.py:9` import `ANPR_MAX_FILES_PER_REQUEST` từ `app.core.constants`. Trên develop không còn hai hằng này: bug-043 (`1ba8c14`) và bug-044 (`2ad639c`) thêm chúng vào `app/core/constants.py`, nhưng khi merge sau refactor ISSUE-023 (ADR-0005, `ace0521`/`fd80a73`) thì phần `constants.py` lấy theo bản đã refactor, nên hai hằng biến mất.
- `import app.api.rest.routes.anpr_controller` báo `ImportError`. Router REST ANPR/Vision không nạp được, nên service REST không khởi động.
- `python -m unittest discover -s test` báo 3 lỗi import: `test_anpr_rest_upload`, `test_copilot_streaming_api`, `test_forecast_service`.

## Hành vi mong đợi

Hai hằng có trong `app/core/constants.py` đúng như hồ sơ bug-043/bug-044 mô tả (8 MB mỗi ảnh, tối đa 10 ảnh mỗi request).

## Tái hiện

1. Checkout `origin/develop` (`3abde8c`).
2. `python -c "import app.api.rest.routes.anpr_controller"` báo `ImportError: cannot import name 'ANPR_MAX_IMAGE_BYTES'`.

## Sửa / kiểm chứng

- Thêm lại `ANPR_MAX_IMAGE_BYTES = 8 * 1024 * 1024` và `ANPR_MAX_FILES_PER_REQUEST = 10` vào mục Vision của `app/core/constants.py`. Đặt ở đây vì REST `/anpr/*` và `/vision/recognize` cùng dùng.
- `python -m unittest discover -s test`: hết 3 lỗi import.
