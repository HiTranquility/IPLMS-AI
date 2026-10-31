# 🐛 bug-043: REST ANPR đọc cả file upload vào RAM, không giới hạn kích thước, không kiểm loại file

> **Đích:** `docs/projects/bugs/bug-043-anpr-rest-doc-anh-khong-gioi-han-kich-thuoc/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed — Đã sửa trong PR #113 và bug-050 (giới hạn 8MB upload ảnh REST ANPR). |
| **Ngày đóng** | 2026-10-31 |
| **Người nhận** | @HiTranquility |
| **Ưu tiên** | 🟠 |
| **Người báo** | Claude Code, từ [AUDIT-008](../../audits/10-2026/AUDIT-008-loi-vao-inference-rate-limit-upload-cors-grpc.md) A1 + B1 |
| **Ngày báo** | 2026-10-27 |
| **Môi trường** | develop `f25b747`, process inference (`app.main`, REST :8000) |

## Hành vi thực tế

1. `POST /api/anpr/recognize` gọi `AnprService.recognize`. Hàm này chạy `image_bytes = await file.read()`, đọc **toàn bộ** file vào RAM mà không có trần byte.
2. Không kiểm `content_type` hay magic byte. File `text/plain` cũng được đưa vào `cv2.imdecode`.
3. Khi lỗi, controller trả `f"Recognition failed: {exc}"`, tức là đưa nguyên chuỗi exception (có thể chứa đường dẫn file, tên model) về client.

Mức 🟠 chứ không 🔴 vì process inference không ra Internet: compose bind `127.0.0.1`, Helm không có ingress tới AI. Còn lại hai đường gọi được: pod trong cụm (NetworkPolicy chưa bật ở prod, AUDIT-008 B3) và trình duyệt của developer qua CORS mở ([bug-045](../bug-045-cors-inference-phan-chieu-moi-origin-kem-credentials/bug.md)).

## Hành vi mong đợi

- Đọc tối đa `N + 1` byte giống chuẩn ANPR thử của Console (`console_tools_controller.py:188`, N = 8 MB), vượt thì trả **413**.
- Chỉ nhận `image/jpeg` và `image/png`, và magic byte phải khớp. Sai thì trả **415**.
- Lỗi trả mã chung (ví dụ `ANPR_FAILED`); chi tiết chỉ ghi vào log kèm `request_id`.

## Tái hiện

Dùng `TestClient` trong process, thay `AnprService.recognize_bytes` bằng stub ghi lại số byte nhận được và ném exception:

```python
c.post("/api/anpr/recognize", files={"file": ("x.txt", b"A" * (60*1024*1024), "text/plain")})
```

Kết quả: `200`, stub nhận **62 914 560 byte**, message là `Recognition failed: stub: /secret/path/model.pt not found`.

## Bằng chứng

- `app/core/vision/services/anpr_service.py:18`: `image_bytes = await file.read()`
- `app/api/rest/routes/anpr_controller.py:17-24`: không kiểm loại file, trả `str(exc)`
- Chuẩn vàng: `app/api/rest/routes/console_tools_controller.py:188`: `await file.read(KNOWLEDGE_MAX_FILE_BYTES + 1)`
- Trần RAM pod: `docker-compose.production.yml` (`limits.memory: 2G`)

## Sửa / kiểm chứng

- `app/api/rest/image_upload.py` (mới): `read_image_upload` đọc tối đa `ANPR_MAX_IMAGE_BYTES + 1` (8 MB, `app/core/constants.py`), vượt thì **413**; magic byte không phải JPEG/PNG thì **415**. Áp cho `/anpr/recognize`, `/anpr/recognize-many`, `/vision/recognize`.
- `AnprService.recognize` nhận bytes đã kiểm thay vì `UploadFile` (`app/core/vision/services/anpr_service.py`).
- `/anpr/recognize` trả `Recognition failed`; chi tiết exception chỉ ghi vào log (`logger.exception`).
- Kiểm: `python -m unittest test.test_anpr_rest_upload`: 4/4 (60 MB → 413, `text/plain` khai `image/jpeg` → 415, JPEG/PNG → tới engine, message lỗi không chứa chuỗi exception). Bộ đầy đủ 593 test: còn đúng 7 lỗi có sẵn trên `develop` (thiếu stub gRPC trong worktree mới; 2 test RAG `no_context`), không lỗi mới.
- Chưa làm: chưa thử trên stack dev với model thật.
