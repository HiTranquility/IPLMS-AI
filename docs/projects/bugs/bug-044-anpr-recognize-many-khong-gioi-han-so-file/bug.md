# 🐛 bug-044: `/anpr/recognize-many` nhận tới 1000 file mỗi request và chạy ANPR tuần tự từng file

> **Đích:** `docs/projects/bugs/bug-044-anpr-recognize-many-khong-gioi-han-so-file/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed — Đã sửa trong PR #113 (giới hạn 10 file per request cho recognize-many). |
| **Ngày đóng** | 2026-10-31 |
| **Người nhận** | @HiTranquility |
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

- Nhánh **xếp chồng trên bug-043** (cùng hàm, dùng `read_image_upload`): merge bug-043 trước.
- `ANPR_MAX_FILES_PER_REQUEST = 10` (`app/core/constants.py`); vượt thì **413** trước khi đọc ảnh nào. Mọi ảnh được đọc và kiểm định dạng trước, rồi mới chạy engine (`app/api/rest/routes/anpr_controller.py`).
- Kiểm: `test.test_anpr_rest_upload` 7/7 (11 ảnh → 413; ảnh hỏng cuối lô → 415 và không ảnh nào tới engine; 10 ảnh → chạy đủ 10).
- Không tìm thấy caller nào của `/anpr/recognize-many` trong `backend/`, `frontend/`, `ai/ui/`, `mobile/`; endpoint được giữ, chưa bỏ.
