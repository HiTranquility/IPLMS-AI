# 🐛 bug-045: CORS của REST inference phản chiếu mọi origin kèm `allow-credentials: true`

> **Đích:** `docs/projects/bugs/bug-045-cors-inference-phan-chieu-moi-origin-kem-credentials/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed — Đã sửa trong PR #115 (CORS inference theo allowlist, bỏ wildcard credentials). |
| **Ngày đóng** | 2026-10-31 |
| **Người nhận** | @HiTranquility |
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

- `ServerConfig.cors_allow_origins` (env `AI_CORS_ALLOW_ORIGINS`, CSV, mặc định rỗng) trong `app/config/server_config.py`; ghi vào `.env.example`.
- `register_cors` (`app/api/rest/middlewares/cors.py`): danh sách rỗng thì không gắn middleware; có danh sách thì chỉ các origin đó, `allow_credentials=False`, chỉ `GET`/`POST`.
- Đã grep: không màn nào của `ai/ui` hay `frontend/` gọi thẳng `:8000`, nên mặc định rỗng không làm gãy màn nào.
- Kiểm: `test.test_cors_policy` 3/3 (origin lạ không có header, kể cả khi gửi Cookie; origin trong danh sách được qua, không kèm credentials); `test.test_config` xanh; bộ đầy đủ chỉ còn 7 lỗi có sẵn.
