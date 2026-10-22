# IPLMS AI

Dịch vụ Python/FastAPI + gRPC cho ANPR, Copilot/Knowledge và vòng đời model.
Backend gọi qua gateway; Forecast chưa được bật phục vụ vì chưa có model qua gate.

- [DESIGN.md](DESIGN.md): kiến trúc, data flow, môi trường Traefik, quyết định và ngoại lệ; runbook chi tiết.
- [AI_CONVENTIONS](docs/standards/AI_CONVENTIONS.md): luật phân tầng và naming.
- [Contract cấu hình mẫu](.env.example): tên biến và giá trị mẫu, không chứa cấu hình thật.

## Bắt đầu

Từ thư mục `ai/`, chạy `./setup-dev.ps1` (Windows) hoặc `./setup-dev.sh` (Linux/macOS).
Script chuẩn bị môi trường local; xem [hướng dẫn trong DESIGN](DESIGN.md) trước khi chạy.
Build Docker cần context ở gốc umbrella để lấy `proto/`.

```bash
# Develop: source mount, reload; Traefik chọn traefik.develop.yml.
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.develop.yml up -d

# Production: image dựng sẵn; Traefik chọn traefik.production.yml.
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.production.yml up -d --no-build
```

Cần mạng chung `iplms-shared-dev` (`SHARED_NETWORK`, do stack backend tạo) tồn tại; full stack dùng `deployment/script/run-stack.ps1`
hoặc `.sh` ở umbrella. `.env.dev`/`.env.prod` giữ tên hợp đồng runtime, không commit.
AI có database pgvector riêng `database-vector`. REST ở localhost:8000, gRPC localhost:50051;
dashboard localhost:8080 chỉ bật ở develop. Base không thay thế cấu hình production.

## Kiểm nhanh

```bash
python -m unittest discover -s test -t .
python -m training.readiness --scope vision
python -m training.readiness --scope forecast
```

Lệnh test/readiness cần môi trường và dữ liệu phù hợp; readiness fail không phải lý do bật Forecast giả.
Health endpoint: `GET /health`. Luồng domain và giới hạn đo chất lượng ở [DESIGN](DESIGN.md).
