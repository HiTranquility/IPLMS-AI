# 🐛 bug-045: CORS của REST inference phản chiếu mọi origin kèm `allow-credentials: true`

> **Đích:** `docs/projects/bugs/bug-045-cors-inference-phan-chieu-moi-origin-kem-credentials/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New |
| **Ưu tiên** | 🟠 |
| **Người báo** | Claude Code, từ [AUDIT-008](../../audits/10-2026/AUDIT-008-loi-vao-inference-rate-limit-upload-cors-grpc.md) A3 |
| **Ngày báo** | 2026-10-27 |
| **Môi trường** | develop `f25b747`, mọi môi trường: `docker-compose.production.yml` không ghi đè |

## Hành vi thực tế

`register_cors` gắn `CORSMiddleware(allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])` cho process inference. Với cấu hình này, Starlette trả lại đúng origin của request kèm `access-control-allow-credentials: true`.

AI không có xác thực (rào bug-032 dựa vào việc chỉ bind localhost). Hệ quả là **bất kỳ trang web nào** developer đang mở cũng gọi được `http://127.0.0.1:8000` và **đọc được phản hồi**: Copilot, forecast, ANPR. Trang đó cũng đốt được CPU và token LLM của máy. CORS mở chính là đường vòng qua rào "chỉ localhost".

Docstring ở `cors.py:9-10` đã ghi production phải thu hẹp, nhưng chưa có config nào làm việc đó.

## Hành vi mong đợi

- `allow_origins` đọc từ config. Production để rỗng, vì backend gọi server-to-server và không cần CORS. Dev chỉ liệt kê origin của UI dev nếu thật sự có màn gọi thẳng.
- Bỏ `allow_credentials` vì REST inference không dùng cookie.

## Tái hiện

Dùng `TestClient` với một app chỉ có `register_cors`:

| Request | `access-control-allow-origin` | `access-control-allow-credentials` |
|---|---|---|
| `OPTIONS`, `Origin: https://evil.example`, `Access-Control-Request-Method: POST` | `https://evil.example` | `true` |
| `GET`, `Origin: https://evil.example`, có `Cookie` | `https://evil.example` | `true` |

## Bằng chứng

- `app/api/rest/middlewares/cors.py:14-15`
- `app/main.py:39`: `register_cors(app)`
- `docker-compose.yml:150`: ghi chú bug-032 "AI không có xác thực"

## Sửa / kiểm chứng

Chưa sửa. Khi sửa, thêm test: preflight với origin lạ không có header `access-control-allow-origin`; origin trong danh sách vẫn qua. Grep `fetch(`/`axios` trỏ tới `:8000` trong `ui/` và `frontend/` để chắc không màn nào gọi thẳng inference từ trình duyệt.
