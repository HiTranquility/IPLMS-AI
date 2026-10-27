# 🐛 bug-046: Lối vào AI không giới hạn tốc độ và số request đồng thời (Traefik không middleware, gRPC không trần RPC)

> **Đích:** `docs/projects/bugs/bug-046-loi-vao-ai-khong-gioi-han-toc-do-va-dong-thoi/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New |
| **Ưu tiên** | 🟠 |
| **Người báo** | Claude Code, từ [AUDIT-008](../../audits/10-2026/AUDIT-008-loi-vao-inference-rate-limit-upload-cors-grpc.md) A4 |
| **Ngày báo** | 2026-10-27 |
| **Môi trường** | develop `f25b747`; compose (có Traefik) và Helm K3s (không có Traefik trước AI) |

## Hành vi thực tế

1. **Traefik** (`docker/traefik/traefik.yml`, `traefik.production.yml`) có cân bằng tải và healthcheck, nhưng không khai báo middleware `rateLimit` hay `inFlightReq`. Router `ai-rest` và `ai-grpc` trong `docker-compose.yml` cũng không gắn middleware nào.
2. **gRPC server** (`app/grpc_server.py:37-44`) tạo `aio.server` với `ThreadPoolExecutor(max_workers=10)` nhưng không đặt `maximum_concurrent_rpcs`. Request vượt 10 worker xếp hàng không trần thay vì bị từ chối sớm.
3. **Helm**: backend gọi thẳng ClusterIP của AI, không qua gateway nào, nên ở K3s chẳng có lớp giới hạn nào.
4. Phía backend, `RateLimitGuard` có sẵn nhưng không gắn cho 3 route upload ANPR của staff (AUDIT-008 B4). Thành ra không chỗ nào chặn burst trên đường check-in.

Hệ quả: một đợt burst (camera gửi lặp, client retry, hoặc staff bị lộ tài khoản) làm hàng đợi gRPC phình, latency check-in tăng và timeout hàng loạt. AI ở prod chỉ có 1 replica (AUDIT-008 B5), nên không có bản nào khác gánh hộ.

## Hành vi mong đợi

- `aio.server(..., maximum_concurrent_rpcs=<config>)`: khi đầy thì trả `RESOURCE_EXHAUSTED` ngay, để backend fallback hoặc báo lỗi rõ. Cách này chạy được cả ở compose lẫn Helm.
- Traefik: middleware `inFlightReq` + `rateLimit` cho router `ai-rest`, khai báo cùng lúc ở `traefik.yml` và `traefik.production.yml`.
- Có metric cho số request bị từ chối do quá tải (Prometheus đã có ở entrypoint `metrics`).

## Tái hiện

Bằng chứng từ cấu hình (chưa chạy tải):

```bash
grep -niE "ratelimit|inflightreq|middlewares" docker/traefik/*.yml docker-compose*.yml   # 0 dòng
grep -n "maximum_concurrent_rpcs" app/grpc_server.py                                     # 0 dòng
```

Muốn đo thật thì dùng `ghz` gọi `VisionService` với concurrency 50 trên stack dev và xem p95 cùng số request timeout. Chưa chạy: cần dựng stack và có model.

## Bằng chứng

- `docker/traefik/traefik.yml:23-31`, `docker/traefik/traefik.production.yml:23-31`
- `docker-compose.yml:45-65` (label router không có middleware)
- `app/grpc_server.py:37-44`; `app/config/server_config.py:14` (`grpc_max_workers: int = 10`)
- `deployment/helm/iplms/values-prod.yaml:57-60` (AI 1 replica)

## Sửa / kiểm chứng

Chưa sửa. Khi sửa, thêm test gRPC: chạy song song `maximum_concurrent_rpcs + 1` RPC chậm, RPC dư phải nhận `RESOURCE_EXHAUSTED`. Chạy `docker compose config` để chắc label middleware hợp lệ.
