# 🐛 bug-044: `/anpr/recognize-many` nhận tới 1000 file mỗi request và chạy ANPR tuần tự từng file

> **Đích:** `docs/projects/bugs/bug-044-anpr-recognize-many-khong-gioi-han-so-file/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New |
| **Ưu tiên** | 🟠 |
| **Người báo** | Claude Code, từ [AUDIT-008](../../audits/10-2026/AUDIT-008-loi-vao-inference-rate-limit-upload-cors-grpc.md) A2 |
| **Ngày báo** | 2026-10-27 |
| **Môi trường** | develop `f25b747`, process inference (REST :8000), Starlette 1.6.0 |

## Hành vi thực tế

`POST /api/anpr/recognize-many` nhận `List[UploadFile]` mà không đặt trần. Giới hạn duy nhất là mặc định `max_files=1000` của `Request.form()` trong Starlette. Mỗi file đi qua YOLO + OCR tuần tự trong cùng request, và từng file lại dính lỗi đọc không giới hạn của [bug-043](../bug-043-anpr-rest-doc-anh-khong-gioi-han-kich-thuoc/bug.md).

Một request vì vậy giữ CPU trong thời gian bằng số file nhân thời gian ANPR một ảnh. CPU này dùng chung với đường nóng gRPC check-in/check-out của backend.

## Hành vi mong đợi

- Trần số file (đề xuất 10) và trần tổng byte của request; vượt thì trả **413** trước khi chạy ANPR.
- Nếu không còn caller nào dùng endpoint này (đường nóng của backend đi gRPC) thì cân nhắc bỏ hẳn.

## Tái hiện

Dùng `TestClient` trong process với stub `recognize_bytes`, gửi 500 file JPEG 1 byte trong một request:

```python
c.post("/api/anpr/recognize-many", files=[("files", (f"{i}.jpg", b"B", "image/jpeg")) for i in range(500)])
```

Kết quả: `200`, stub được gọi **500 lần**.

## Bằng chứng

- `app/api/rest/routes/anpr_controller.py:28-46`
- `starlette.requests.Request.form(max_files=1000, ...)`, Starlette 1.6.0 trong `ai/.venv`

## Sửa / kiểm chứng

Chưa sửa. Khi sửa, thêm test: 11 file → 413, 3 file → 200. Grep caller của `/anpr/recognize-many` trong `backend/`, `frontend/`, `ui/` trước khi quyết định bỏ endpoint.
