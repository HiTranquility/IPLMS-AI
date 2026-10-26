# 🐛 bug-031: Gateway Traefik của AI nhặt container của project khác trên cùng máy

> **Đích:** `docs/projects/bugs/bug-031-gateway-nhat-container-project-khac/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility (Claude Code viết) |
| **Hạn** | — |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | 2026-10-26 |
| **Ngày báo** | 2026-10-26 |
| **Người báo** | Claude Code (lúc bật Prometheus/Grafana để xem tải 2 replica) |
| **Môi trường** | local (stack `iplms-ai-dev` chạy chung máy với `eshop-backend-dev`) |

## Hành vi thực tế

Gateway (`traefik:v3.6.16`) đọc socket Docker của cả máy và nhận mọi container có `traefik.enable=true`, kể cả container của project khác. Trên máy dev, nó nhận `eshop-backend-dev-api-1` thành router `api@docker` với luật `Host(localhost)`. Router này không khai `entryPoints`, nên gắn vào cả ba cổng của AI: `rest`, `grpc` và `metrics`.

Luật `Host(localhost)` có độ ưu tiên cao hơn `PathPrefix(/)` của AI. Hiện router đó chưa nhận request chỉ vì middleware `compress@file` không tồn tại ở AI, nên Traefik tắt router và log lỗi liên tục. Nếu bên eShop bỏ middleware này, mọi request vào `http://localhost:8000` (và cổng gRPC) sẽ bị đẩy sang eShop. Ngoài ra, health check của service `api@docker` lỗi mỗi 10 giây.

## Hành vi mong đợi

Gateway AI chỉ định tuyến tới container của chính stack AI.

## Tái hiện

1. Chạy `iplms-ai-dev` và một stack khác trên cùng Docker, trong đó stack kia có label `traefik.enable=true` (vd eShop).
2. `docker logs iplms-ai-dev-gateway-1`: thấy `routerName":"api@docker"`, `middleware "compress@file" does not exist` ở các entrypoint `rest`, `grpc`, `metrics`, cùng `Health check failed` cho `http://172.21.0.3:8080`.

## Bằng chứng

- `docker/traefik/traefik.yml` (và bản `develop`, `production`): `providers.docker` chỉ có `exposedByDefault: false`, không có ràng buộc nào.
- Label của container eShop: `traefik.http.routers.api.rule=Host(\`api.eshop.local\`) || Host(\`localhost\`)`, không có `entrypoints`.

## Sửa / kiểm chứng

- 3 file `docker/traefik/traefik*.yml`: thêm `constraints: "Label(\`iplms.gateway\`, \`ai\`)"`.
- `docker-compose.yml`: service `api` thêm nhãn `iplms.gateway=ai`.
- Cùng lượt (tối ưu gateway): Traefik tự dò sức khoẻ từng replica (5 s, timeout 2 s). `ai-rest` gọi `GET /health`. `ai-grpc` gọi `grpc.health.v1` ngay trên cổng gRPC (`mode=grpc`; `proto/health_service.proto`, `app/grpc_server.py:26`), nên bắt được cả trường hợp gRPC treo trong khi REST vẫn sống. Ban đầu dò REST `:8000` với lý do sai; audit-1 A-1 bắt lỗi, đã đổi.
- `DESIGN.md` §Traefik: ghi ràng buộc nhãn và health check.

Kiểm trên stack dev (2 replica):
- `docker compose config -q` OK.
- Sau khi tạo lại `api` và restart `gateway`: 28 dòng log, 0 dòng dính `api@docker`/eShop.
- `http://localhost:8000/health`: 20/20 trả 200.
- Prometheus `traefik_service_server_up` = 1 cho cả 4 server (2 REST, 2 gRPC).
- Tắt `api-2`: 20/20 vẫn trả 200, Traefik dồn hết sang `api-1`.
- Sau khi đổi sang `mode=grpc`: không có cảnh báo health check trong log gateway; `server_up` = 1 cho 2 server `ai-grpc`; tắt `api-2` thì cả `ai-rest` và `ai-grpc` chỉ còn `api-1`.

Chưa kiểm:
- Compose production trên host thật.
- Gọi gRPC qua backend NestJS sau thay đổi.
