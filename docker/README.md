# `docker/` — cấu hình đi kèm compose

## `traefik/` — gateway của AI

| File | Dùng khi | Dashboard `:8080` |
|---|---|---|
| `traefik.yml` | Chỉ có `docker-compose.yml` | Tắt (`insecure: false`), chỉ còn `/ping` |
| `traefik.develop.yml` | Thêm `-f docker-compose.develop.yml` | Bật, không xác thực; trace lấy mẫu 100% |
| `traefik.production.yml` | Thêm `-f docker-compose.production.yml` | Tắt |

- Mỗi file là cấu hình **đầy đủ**, compose mount đúng một file vào `/etc/traefik/traefik.yml`; không phải lớp chồng lên nhau.
- Provider Docker chỉ nhận container có nhãn `iplms.gateway=ai` (bug-031): container của project khác trên cùng máy không bị kéo vào.
- Entrypoint: `rest :8000`, `grpc :50051` (h2c), `traefik :8080` (ping, dashboard), `metrics :8082` (Prometheus).

Kiểm nhanh khi chạy develop:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/dashboard/   # 200
curl -s http://127.0.0.1:8080/api/http/routers                                # có ai-rest@docker, ai-grpc@docker
```

Dashboard trả 404 tức là gateway đang chạy bằng `traefik.yml`: dựng lại riêng gateway với file develop,

```bash
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.develop.yml up -d --no-deps gateway
```

## `database-vector/init/` — khởi tạo PostgreSQL + pgvector

Chạy **một lần**, chỉ khi volume `database-vector-data` còn mới (cơ chế `docker-entrypoint-initdb.d` của image Postgres).

| Script | Tạo |
|---|---|
| `10-ai-console.sh` | Database `ai_console` và user riêng cho AI Console (mật khẩu lấy từ `AI_CONSOLE_DB_PASSWORD`) |
| `11-ai-inference-role.sh` | Role riêng cho process inference (mật khẩu từ `AI_INFERENCE_DB_PASSWORD`) |

Volume đã có dữ liệu thì sửa script không có tác dụng: tạo DB/role bằng tay hoặc xoá volume (mất dữ liệu tri thức và console). Sau khi tạo, siết quyền bằng `python -m app.script.harden_console_db`.
