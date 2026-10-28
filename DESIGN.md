# DESIGN — IPLMS AI

Trạng thái: thiết kế hiện hành; đối chiếu cấu trúc/config ngày 2026-10-14, chưa chạy model hay chứng nhận chất lượng production trong lần rà này. Người viết: Codex.
Luật code: [AI_CONVENTIONS](docs/standards/AI_CONVENTIONS.md). Điểm vào: [README](README.md).
Trong umbrella, xem thêm [naming chung](../docs/standards/NAMING_CONVENTIONS.md); clone riêng vẫn đọc được thiết kế và conventions tại đây.

## Quyết định thiết kế, UI và ngoại lệ

AI phục vụ backend qua gRPC và REST, không sở hữu UI sản phẩm hay bảng màu. Trang dev `/dashboard` (ngoại lệ 16/10/2026) **đã bỏ** ngày 17/10/2026: kiểm cấu hình, hỏi thử Copilot và nạp bản nháp tri thức nằm ở trang "Công cụ thử" của AI Console, chạy trong process console, có quyền + audit (IPLMS ADR-0050). Màu/token của màn hình Copilot, ANPR và quản lý model thuộc DESIGN của app frontend tương ứng. Dashboard Traefik là UI vận hành của phần mềm bên thứ ba; không dùng nó làm design system của IPLMS.

**Ngoại lệ có phạm vi — AI Console nội bộ (IPLMS ADR-0048, ADR-0049, ADR-0051):** công cụ chuyên sâu cho bộ phận AI, **không phải UI sản phẩm**. Chạy process riêng `app/console_main.py` (service compose `console`, bật bằng `--profile console`), chỉ publish `127.0.0.1:8090`, không label Traefik, không CDN, tắt `/docs`. DB riêng `ai_console` (user riêng, tạo bởi `docker/database-vector/init/10-ai-console.sh` khi volume `database-vector` mới). Quyền nằm ở DB console (`app/core/console/engines/access_policy.py`), không lấy từ Admin/Moderator. Đăng nhập Google + TOTP bắt buộc; admin khẩn cấp tạo bằng `python -m app.script.console_admin`. Telemetry request AI **không** ở DB console mà ở `database-vector` (ADR-0049): bảng `ai_request_log` do `CopilotService` ghi nền sau mỗi lượt (`app/core/copilot/services/usage_service.py`), câu chữ che PII, user băm HMAC, chi phí chỉ tính khi cấu hình giá; đọc qua RPC `CopilotService.GetUsageSummary`, 👍/👎 qua `RecordFeedback`. Giao diện [`ai/ui`](ui/DESIGN.md) (React + Vite, build ra `ui/dist`, `console_main` phục vụ tại `/` kèm CSP `'self'`; compose mount `./ui/dist`) theo 8 luật Hallmark của `frontend/DESIGN.md` §4. Copilot Lab đọc `ai_request_log` qua `AI_DATABASE_URL` (cùng `.env.dev`), kết quả chấm lượt nằm ở bảng `copilot_turn_review` của DB console kèm audit; tỉ lệ đúng chỉ tính trên lượt đã chấm. Vision (P3–P5): backend đẩy ảnh cắt + nhãn qua RPC `DatasetService.ExportForConsole` (kênh A2, group/area đã HMAC) — process gRPC ghi vào DB console (`app/infra/database/console_vision_store.py`, cần `AI_CONSOLE_DATABASE_URL`); nhãn console có provenance riêng, duyệt bốn mắt; snapshot train loại nhóm đã vào golden đã khoá; lượt đo chạy `evaluation_service` trên ảnh trong DB console; model và accept policy promote/duyệt bởi người khác người đề xuất kèm step-up. Ngưỡng đã duyệt: backend kéo qua RPC `DatasetService.GetAcceptPolicy` mỗi chu kỳ A2 (IPLMS ADR-0051) — process gRPC chỉ đọc `accept_policy` ở DB console.

**Ngoại lệ dev/sandbox — mẫu thực hành Vision Lab ([bug-013](docs/projects/bugs/bug-013-vision-demo-seed-khong-chan-production/bug.md)):** `vision_sample`/`vision_crop`/`vision_label` bình thường chỉ nhận dữ liệu qua kênh A2. `POST /api/vision/seed-demo` ghi thêm 7 biển số mẫu (capture id `a0000000-…`, nhãn mẫu đứng tên một thành viên khác người bấm, có `audit_event`) chỉ khi `AI_CONSOLE_DEMO_SEED_ENABLED=true` — bật ở `docker-compose.develop.yml`, base/production mặc định tắt (403).

Volume `database-vector` đã có dữ liệu thì tạo DB console bằng tay (thay mật khẩu, không dán vào log):
`printf '%s\n' "CREATE ROLE ai_console LOGIN PASSWORD :'pw';" "CREATE DATABASE ai_console OWNER ai_console;" | docker compose exec -T database-vector psql -U postgres -v ON_ERROR_STOP=1 -v pw='<mật khẩu>'` — phải qua stdin: `psql -c` không thay biến `:'pw'`.

Luồng chính: backend → gateway → REST/gRPC handler → service domain → engine → adapter. Mapper đổi protobuf ↔ DTO tại biên; business core không phụ thuộc transport. DB nghiệp vụ thuộc backend; `database-vector` giữ tri thức/vector của AI. Training/checkpoint là vòng đời offline, không đồng nghĩa model đã được phép phục vụ.

Nguồn đối chiếu: [REST router](app/api/rest/router.py), [gRPC server](app/grpc_server.py), [config tổng](app/config/app_config.py), [Forecast service](app/core/forecast/services/forecast_service.py), [Compose base](docker-compose.yml). Forecast Service đã được kích hoạt (ADR-0037), phục vụ dự báo tỷ lệ lấp đầy và đề xuất giá động (surge pricing) kết nối ClickHouse Data Marts (`AreaOccupancyTelemetryItem`).

| Vai trò | Compose ghép với base | Static Traefik được mount | Dashboard / trace |
|---|---|---|---|
| Base local | `docker-compose.yml` | [traefik.yml](docker/traefik/traefik.yml) | `insecure: false`, sample 0.1 |
| Develop | [docker-compose.develop.yml](docker-compose.develop.yml) | [traefik.develop.yml](docker/traefik/traefik.develop.yml) | `insecure: true`, sample 1.0; host bind localhost |
| Production | [docker-compose.production.yml](docker-compose.production.yml) | [traefik.production.yml](docker/traefik/traefik.production.yml) | `insecure: false`, sample 0.1 |

Mỗi static Traefik file là một cấu hình **đầy đủ**, không phải YAML overlay. Compose chọn file source theo môi trường nhưng target luôn `/etc/traefik/traefik.yml`; mount Docker socket kế thừa base. REST `8000`, gRPC `50051`, ping/dashboard `8080`, Prometheus `8082`; metrics và Tempo thuộc mạng nội bộ. Production giữ ping cho healthcheck nhưng không bật API dashboard không xác thực. Cả 3 file đặt `providers.docker.constraints` theo nhãn `iplms.gateway=ai`: socket Docker thấy mọi container trên máy, nên gateway chỉ nhận container mang nhãn này (bug-031). Traefik tự dò sức khoẻ từng replica mỗi 5 s: `ai-rest` gọi `GET /health`, `ai-grpc` gọi `grpc.health.v1` ngay trên cổng gRPC (`mode=grpc`), nên replica hỏng bị gỡ khỏi vòng chia tải và Prometheus có `traefik_service_server_up` theo từng replica. Giới hạn tải (bug-046): router `ai-rest` gắn middleware `inFlightReq` (mặc định 20) + `rateLimit` (30/s, burst 60) qua label compose; gRPC không gắn middleware vì stream Copilot sống lâu, trần nằm trong process ở `AI_GRPC_MAXIMUM_CONCURRENT_RPCS` (mặc định 50, vượt thì `RESOURCE_EXHAUSTED`). Helm gọi thẳng ClusterIP, không có Traefik, nên chỉ còn trần trong process. Tên file `production` không tự cung cấp TLS hay xác thực cho AI: gateway vẫn chỉ bind host localhost, backend gọi mạng nội bộ.

| Ngoại lệ / tên cần phân biệt | Phạm vi và lý do | Khi thay đổi / kết thúc |
|---|---|---|
| `.env.dev`, `.env.prod` so với `develop`, `production` | Hợp đồng runtime hiện có của setup/config/Compose | Chỉ đổi khi caller và cơ chế cấp config đổi cùng lúc |
| `/etc/traefik/traefik.yml` | Tên config bên trong container, giống nhau cho mọi môi trường | Chỉ đổi cùng loader/command của Traefik |
| `gateway` / alias `ai-gateway` / mạng chung `iplms-shared-<env>` | Tên service theo vai, alias plane cho stack khác gọi (IPLMS ADR-0055) | Migration phải cập nhật caller, label Docker network và stack script |
| `model/architectures/m1`, `m2` | Tên phiên bản mã kiến trúc nhập từ nguồn ngoài | Đổi cùng registry/import/checkpoint metadata, không rename weights |
| `knowledge_eval` chưa có DTO riêng | Nợ cấu trúc đã ghi ở conventions; không tạo thư mục rỗng | Thêm DTO thật khi thay đổi hợp đồng domain |
| Proto generated | Stub là output của proto nguồn chuẩn ở umbrella | Sinh lại, không sửa tay tên symbol/field tag |

File REST mới dùng `<domain>_controller.py`; health nay là `health_controller.py`, vẫn giữ URL `/health`.
`AI_*` là env key, Python dùng snake_case cho module/hàm và PascalCase cho type. Mọi exception mới phải có phạm vi, lý do và điều kiện bỏ như bảng trên.

Các phần bên dưới bảo toàn bản mô tả kiến trúc và runbook đã có trong README cũ; các số đo/chứng nhận cũ cần chạy lại trước khi dùng làm bằng chứng triển khai hiện tại.

Module **Python độc lập** (ngang hàng `frontend/`, `backend/`): dịch vụ **FastAPI + Docker** xử lý ảnh biển số, chạy xuyên suốt để `backend` gọi ở khâu **check-in / check-out** cổng.

**Nguồn gốc code — đọc trước khi sửa:**
- **Kiến trúc layered** `app/{api,config,core,infra,util}` + `static/{cropped,original}` — theo một layout ALPR có sẵn, không tự nghĩ ra ở đây.
- **Engine ALPR** (YOLO detect + EasyOCR / ONNX Runtime tối ưu tốc độ 10x kèm xử lý biển 2 dòng chuẩn Việt Nam) ở `app/core/vision/engines/` — tối ưu hóa inference độ trễ thấp phục vụ check-in / check-out.
- **CNN phân loại ảnh** (`model/architectures/m1`, `model/architectures/m2`) cũng là **code + kiến trúc bên thứ ba**, ở đây dùng làm **tầng phân loại xe (tuỳ chọn)**.

## 📁 Cấu trúc

Layout theo quy chuẩn `api / config / core / infra / util` —
**transport ở ngoài, nghiệp vụ ở trong**, không tầng nào import ngược lên tầng trên.

```
ai/
├── app/
│   ├── api/                         # TẦNG TRANSPORT — không chứa nghiệp vụ
│   │   ├── grpc/                    #   đường nóng: NestJS backend gọi vào
│   │   │   ├── handlers/            #     vision|copilot|forecast_handler.py — 1 proto service = 1 handler
│   │   │   ├── mappers/             #     *_mapper.py — DTO ↔ message protobuf
│   │   │   ├── interceptors/        #     logging_interceptor.py — log + exception → gRPC status
│   │   │   ├── generated/           #     stub sinh từ proto (KHÔNG commit)
│   │   │   └── generated_stubs.py   #     nạp stub ĐỘNG — thêm proto không phải sửa file này
│   │   └── rest/                    #   FastAPI: upload ảnh thủ công + healthcheck
│   │       ├── router.py            #     gom route
│   │       └── routes/              #     anpr_controller.py · health_controller.py · forecast_controller.py
│   ├── config/                      # CẤU HÌNH — mỗi nhóm 1 file, gom ở app_config.get_config()
│   │   ├── base_config.py           #   BaseConfig (pydantic-settings, native dev đọc .env.dev)
│   │   ├── server_config.py         #   cổng gRPC/REST, max workers, max message
│   │   ├── vision_config.py         #   YOLO · EasyOCR · CNN phân loại xe
│   │   ├── llm_config.py            #   pgvector DB · embedding · API key
│   │   ├── datalake_config.py       #   export batch + slot occupancy cho forecast
│   │   ├── logging_config.py        #   tên logger · level · format
│   │   └── app_config.py            #   AppConfig gộp + get_config() (lru_cache)
│   ├── core/                        # NGHIỆP VỤ — mỗi domain 1 folder
│   │   ├── vision/                  #   ANPR: engines/anpr/ (engine.py façade + các tầng) · services/
│   │   ├── dataset/                 #   chọn ảnh cho người gán nhãn + khoá snapshot (ISSUE-010)
│   │   ├── copilot/                 #   RAG hỏi đáp: engines/rag_pipeline.py · dispute_workflow (chưa nối)
│   │   ├── knowledge/               #   nạp tài liệu → chunk → embedding → pgvector (bản nháp)
│   │   ├── knowledge_eval/          #   bộ test Copilot + cổng xuất bản (ISSUE-009)
│   │   └── forecast/                #   phục vụ MỞ (ADR-0037); kết nối ClickHouse Data Marts & giá động
│   ├── infra/                       # ADAPTER RA NGOÀI — database/ (pgvector) · datalake/ · llm/
│   ├── util/                        # logger.py · console.py · file.py · generate_url.py · request_metrics.py
│   ├── script/                      # compile_proto.py · smoke/eval/seed · export_parking_sessions.py
│   ├── main.py                      # entrypoint REST (FastAPI app)
│   └── grpc_server.py               # entrypoint gRPC (grpc.aio, cổng 50051)
├── test/                            # unittest stdlib — KHÔNG cần thêm dependency
├── model/                           # một root cho toàn bộ vòng đời model
│   ├── architectures/              # mã kiến trúc CNN: m1 (NetV1) · m2 (NetV2 + SE)
│   ├── artifacts/bootstrap/anpr/   # weight YOLO mẫu duy nhất còn theo Git
│   ├── dataset/                     # snapshot local đã materialize
│   ├── checkpoint/                  # checkpoint train local, weight gitignored
│   └── runs/                        # output theo training run
├── notebook/colab/                 # notebook Colab mỏng, chỉ gọi CLI training
├── var/model-cache/                # artifact tải từ object storage; runtime, gitignored
├── training/                        # script train/eval cho CNN nói trên
├── static/{cropped,original}        # ảnh crop/gốc lưu lúc chạy (gitignored)
├── proto/ → dùng `proto/*.proto` ở GỐC REPO (6 file, nguồn chuẩn dùng chung với backend)
├── Dockerfile · docker-compose.yml · requirements*.txt
```

**Luật tầng:**
- `api/` chỉ điều phối: nhận message → gọi `core/*/services` → `mappers/` dựng protobuf. **Không** nhét nghiệp vụ vào handler.
- `core/*/services` trả **DTO** (pydantic/dataclass), **không** trả `dict` — nhờ vậy mapper và route đều có type.
- Mọi cấu hình đi qua `get_config()`. **Không** `os.getenv` rải rác trong engine/service.
- Đổi hợp đồng → sửa `proto/*.proto` ở gốc repo → chạy lại `compile_proto.py` (và `npm run proto:sync` bên backend).
- Ném exception từ `core/exceptions.py`; `LoggingInterceptor` quy nó về đúng gRPC status. **Không** try/except nuốt lỗi trong handler.

> **Stateless:** backend giữ DB nghiệp vụ bãi xe; AI có database pgvector riêng (`database-vector`) cho Knowledge/Copilot. `PlateResult` là *domain model* (dataclass), không phải ORM.

## 🔀 Luồng xử lý — mỗi domain một README

Mỗi README có: luồng code qua từng file · 🎬 viễn cảnh (sơ đồ mermaid) · 🧰 công nghệ áp dụng · ⚡ case tối ưu (đã làm + nên làm khi nào) · test.

| Domain | Trạng thái | README |
|---|---|---|
| Vision (ANPR + chống tráo xe) | chạy thật | [app/core/vision/README.md](app/core/vision/README.md) |
| Dataset (vòng dữ liệu ANPR) | chạy thật (ISSUE-010) | [app/core/dataset/README.md](app/core/dataset/README.md) |
| Copilot (RAG hỏi đáp) | chạy thật, cần `AI_LLM_API_KEY` | [app/core/copilot/README.md](app/core/copilot/README.md) |
| Knowledge (nạp tài liệu) | chạy thật, cần key cho embedding | [app/core/knowledge/README.md](app/core/knowledge/README.md) |
| Knowledge eval (test + xuất bản) | code xong, chưa chạy với LLM thật | [app/core/knowledge_eval/README.md](app/core/knowledge_eval/README.md) |
| Forecast (dự báo + giá động) | chạy thật (ADR-0037: ClickHouse marts) | [app/core/forecast/README.md](app/core/forecast/README.md) |

## ⚡ Onboarding nhanh (Dành cho Dev mới)

Chạy script tự động thiết lập toàn bộ venv, stubs gRPC, tải EasyOCR model, tạo `.env.dev` từ contract mẫu:

```bash
cd ai

# Trên Windows (PowerShell):
.\setup-dev.ps1

# Trên Linux / macOS:
chmod +x setup-dev.sh
./setup-dev.sh
```

## ▶️ Chạy (Docker)

AI service hỗ trợ chạy riêng rẽ theo 3 chế độ qua Docker Compose:

```bash
cd ai

# 1. Development (khuyến nghị cho dev — mount ./app để hot-reload + nạp .env.dev):
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.develop.yml up -d

# 2. Base (cơ bản, không mount volume):
docker compose --env-file .env.dev up -d

# 3. Production (dùng image build sẵn / ECR, giới hạn CPU/RAM, restart always):
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.production.yml up -d

# Kiểm tra health:
curl http://localhost:8000/health
# Nhận diện ảnh thử:
curl -F "file=@xe.jpg" "http://localhost:8000/api/anpr/recognize?lane_id=gate_in_01"
```

> **Lưu ý Full-stack:** Nếu chạy toàn bộ hệ thống cùng backend, dùng `deployment/script/run-stack.ps1` (hoặc `.sh`). AI chạy trên mạng riêng của stack; chỉ `gateway` nối mạng chung `iplms-shared-dev` (alias `ai-gateway`) để backend gọi (IPLMS ADR-0055).

## ▶️ Chạy local (không Docker)

```bash
cd ai

# Kích hoạt venv (sau khi đã chạy setup-dev)
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 1. Chạy REST API (FastAPI)
uvicorn app.main:app --reload --port 8000

# 2. Chạy gRPC server (lắng nghe [::]:50051 cho backend gọi vào)
python -m app.grpc_server
```

## 🔎 Kiểm readiness Vision / Forecast

Hai lệnh này chỉ đọc dữ liệu và trả exit code khác `0` khi chưa qua gate; chúng
không tự sinh nhãn và không bật endpoint Forecast giả:

```powershell
cd ai
.\.venv\Scripts\python.exe -m training.readiness --scope vision
.\.venv\Scripts\python.exe -m training.readiness --scope forecast
```

Quy trình đầy đủ:

- Vision: [nạp bộ vàng → kiểm checksum/tag → đo exact/CER/latency](data/golden/plates/README.md).
- Forecast: [export session thật → readiness → baseline backtest theo lot/horizon](docs/guides/09-2026/04-forecast-training-strategy.md#quy-trình-chạy-thật-từ-postgresql-đến-baseline-report).
- Notebook Forecast: [`notebook/forecast_experiment.ipynb`](notebook/forecast_experiment.ipynb) chỉ điều phối readiness và runner; không chứa logic train.
- Upload ảnh và đo request gRPC/REST: [guide Postman](../docs/guides/09-2026/test-grpc-ai-with-postman.md).

## 🧠 Copilot RAG & Quản lý tri thức (Knowledge)

Dịch vụ Copilot RAG sử dụng PostgreSQL + pgvector để lưu trữ và truy hồi tri thức nội bộ bãi xe (quy định, biểu phí, hướng dẫn):

```bash
cd ai
.\.venv\Scripts\Activate.ps1  # hoặc source .venv/bin/activate

# 1. Nạp dữ liệu mẫu (quy chế bãi xe vào pgvector):
python app/script/seed_regulations.py

# 2. Nạp tài liệu tri thức (PDF / DOCX / TXT / MD, ≤ 8MB):
#    file là đối số vị trí; bỏ --parking-lot-id = tài liệu chung cho mọi bãi.
#    --parking-lot-id là ID bãi (ParkingArea) mà Copilot của bãi đó sẽ tra.
python -m app.script.ingest_knowledge path/to/quy-che.pdf --parking-lot-id <area-uuid> --category regulation

# 3. Chạy đánh giá chất lượng truy hồi RAG (eval retrieval):
python app/script/eval_retrieval.py
#    Eval end-to-end (LLM thật: trả lời/từ chối, trích nguồn, p50/p95):
python -m app.script.eval_copilot_e2e --dataset data/knowledge/eval_set_heldout.json

# 4. Kiểm tra kết nối gRPC smoke check:
python app/script/grpc_smoke_check.py

# 5. Kiểm tra/export phiên đỗ tăng dần sang data lake local:
$env:AI_DATALAKE_SOURCE_DATABASE_URL = "postgresql://...@localhost:5433/iplms"
python -m app.script.export_parking_sessions --status
python -m app.script.export_parking_sessions --since 2026-09-01T00:00:00Z
python -m training.forecast.run_experiment --as-of 2026-09-25T00:00:00+07:00
```

## ✅ Chạy test

```bash
cd ai
# Chạy toàn bộ test suite (không cần cài thêm dependency):
.\.venv\Scripts\python.exe -m unittest discover -s test -t .
# hoặc:
pytest test
```

Bộ test bao phủ logic ANPR, Enums, DTO Mappers, Copilot RAG Pipeline, Ingestion Service, LLM Factory:

| Nhóm test | File | Mục đích bảo vệ |
|---|---|---|
| ANPR & Vision | `test_generate_url.py`, `test_plate_text.py`, `test_vision_mapper.py` | Format biển số, URL ảnh theo event_id, mapping protobuf DTO |
| gRPC Contract | `test_enums_match_proto.py`, `test_config.py` | Đảm bảo Enum Python khớp từng chữ với proto, config payload max size |
| Copilot & RAG | `test_rag_pipeline.py`, `test_llm_factory.py` | Luồng truy hồi RAG, fallback khi không có context, LLM provider |
| Knowledge Ingest | `test_ingestion_service.py`, `test_embedding_client.py` | Tách chunk tài liệu, metadata, sinh vector embedding |
| Data lake | `test_datalake.py` | Export incremental không PII, manifest/checksum, dedup và nhãn occupancy 30 phút |
| ML readiness/baseline | `test_training_readiness.py`, `test_forecast_training.py` | Gate ảnh/hash/raw export và backtest không impute zero/không leakage |
| Request measurement | `test_request_metrics.py` | Percentile, error rate, throughput, plate-match và benchmark gates |

## ⚙️ Biến môi trường

Development đọc `.env.dev`; production đọc `.env.prod` do secret manager sinh.
Danh sách biến chuẩn nằm trong `.env.example`:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `AI_GRPC_PORT` | `50051` | Cổng gRPC server |
| `AI_FASTAPI_PORT` | `8000` | Cổng REST API |
| `AI_DEVICE` | `cpu` | `cpu` hoặc `cuda` |
| `AI_DATABASE_URL` | `postgresql://...` | Kết nối PostgreSQL hỗ trợ pgvector cho Copilot RAG |
| `AI_DATALAKE_SOURCE_DATABASE_URL` | `postgresql://...` | PostgreSQL nghiệp vụ backend dùng riêng cho export Forecast |
| `AI_LLM_API_KEY` | *(rỗng)* | OpenAI API key cho Copilot và Embedding; chỉ bắt buộc khi `AI_LLM_PROVIDER=openai` (thiếu key → `ModelNotLoadedError`) |
| `AI_LLM_PROVIDER` | `ollama` | `ollama` (Ollama local, không cần key), `local` (llama-server ở `AI_LOCAL_LLM_URL`, không lên thì chuyển sang Ollama) hoặc `openai`. AI **không tự bật** llama-server nữa (đã bỏ `llama_server_manager.ensure_server_running()`, ISSUE-019 A-41): muốn dùng thì chạy server trước; mỗi lần tạo client, `/health` được dò (timeout 0.3 s) ngoài event loop qua `asyncio.to_thread`. Đây chỉ là **dự phòng** khi tác vụ chưa có revision ACTIVE trong `ai_model_profiles`; trang Settings không đổi provider/model nữa, chỉ hiện model inference dùng thật theo tác vụ (IPLMS ADR-0061 §2, ISSUE-022). `openai` gửi câu hỏi ra ngoài nên chỉ bật qua env |
| `AI_OLLAMA_URL` | `http://127.0.0.1:11434/v1` | Endpoint Ollama khi `AI_LLM_BASE_URL` rỗng |
| `AI_LLM_MODEL` | `qwen2.5:0.5b` | Model LLM sinh câu trả lời (vừa VRAM 4 GB); dùng OpenAI thì đặt `gpt-5.6-luna` |
| `AI_CONSOLE_RELOAD` | `false` | Bật reloader cho `python -m app.console_main` (chỉ máy dev) |
| `AI_CONSOLE_MODEL_CONNECTION_HOSTS` | *(rỗng = chặn hết)* | Host được làm endpoint connection ở Models & Connections, phân cách dấu phẩy, khớp đúng tên. Link-local/metadata (`169.254.0.0/16`, `fe80::/10`, `fd00:ec2::254`, `100.100.100.200`) luôn bị chặn sau khi phân giải DNS; probe nối thẳng vào IP đã kiểm, không theo redirect (IPLMS ADR-0061 §7, ISSUE-022). Bảng `ai_model_connections` ở `ai-db` (cùng `AI_DATABASE_URL`), chỉ lưu **tên** biến secret |
| `AI_CONSOLE_MODEL_SECRET_NAMES` | *(rỗng)* | Tên biến env chứa key được phép ngoài tiền tố `AI_LLM_KEY_` (vd `AI_LLM_API_KEY`); tên khác bị từ chối để không gửi nhầm secret khác làm Bearer |
| `AI_CONSOLE_MODEL_TEST_TIMEOUT_SECONDS` / `AI_CONSOLE_MODEL_TESTS_PER_MINUTE` | `10` / `10` | Timeout một lượt thử kết nối; số lần thử mỗi thành viên mỗi 60 s (bộ đếm trong RAM process console, vượt → 429) |
| `AI_RUNTIME_SETTINGS_PATH` | `ai/var/runtime_settings.json` | File cấu hình đổi ở trang Settings; console áp dụng ngay, inference nạp khi khởi động lại. Chỉ đọc từ biến môi trường thật, không đọc `.env.dev` |
| `AI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model sinh vector cho tri thức |
| `AI_EMBEDDING_ALLOW_NO_PGVECTOR` | `false` | Postgres không có pgvector thì dừng với lỗi; `true` (chỉ dev) cho chạy chế độ mảng `DOUBLE PRECISION[]` quét toàn bảng — [ADR-0001](docs/projects/adrs/10-2026/0001-fallback-khong-pgvector-chi-cho-dev.md) |
| `AI_RAG_TOP_K` | `5` | Số chunk tương đồng lấy từ pgvector |
| `AI_RAG_MIN_SIMILARITY` | `0.35` | Ngưỡng cosine tối thiểu của nhánh vector, đồng thời là cổng từ chối: đoạn vector tốt nhất dưới ngưỡng → không gọi LLM. Phụ thuộc model embedding (`bge-m3`: 0.55) — bảng ở [core/copilot](app/core/copilot/README.md#cấu-hình) |
| `AI_DATALAKE_LOCAL_PATH` | `data/datalake` | Workspace raw/manifest/watermark local |
| `AI_DATALAKE_EXPORT_BATCH_SIZE` | `1000` | Số session đọc mỗi batch từ PostgreSQL |
| `AI_DATALAKE_OCCUPANCY_SLOT_MINUTES` | `30` | Độ rộng slot nhãn occupancy |
| `AI_YOLO_MODEL_PATH` | `model/artifacts/bootstrap/anpr/best.pt` | File trọng số YOLO detector |
| `AI_OCR_LANGUAGES` | `en,vi` | Ngôn ngữ nhận diện EasyOCR |
| `AI_VEHICLE_CHECKPOINT` | *(rỗng)* | Checkpoint CNN phân loại xe (để trống = tắt) |

## 🔗 Tích hợp Backend (NestJS)

Backend kết nối tới AI service qua 2 kênh:
1. **gRPC (Kênh chính, thời gian thực):** `AI_GRPC_URL=localhost:50051` cho Copilot RAG (kèm Server-Sent Events / streaming) và ANPR pipeline.
2. **REST (Kênh phụ / upload ảnh thủ công):** `ANPR_SERVICE_URL=http://localhost:8000` cho staff check-in qua endpoint multipart.

## ⚠️ Hiện trạng triển khai

- **ANPR (Vision):** 🟡 Runtime end-to-end hoạt động; bộ vàng hiện `0/200`, nên chưa có accuracy/threshold production được chứng nhận.
- **Copilot RAG:** ✅ Hoạt động đầy đủ (pgvector vector search + chunking + OpenAI embedding & text generation + gRPC ServerStreaming).
- **Forecast (Dự báo chỗ trống):** 🟡 Export/reader, snapshot, point-in-time feature split, baseline/backtest và offline ridge candidate đã có test; local chưa có raw data/capacity history hay candidate được kiểm chứng, nên endpoint tiếp tục từ chối.
- **Anti-fraud (Chống gian lận vé):** 🟡 Skeleton cấu hình sẵn, luật đối soát đang hoàn thiện.

## Tích hợp Khoa — cập nhật 2026-10-16

- Docker giữ contextumbrella và COPYai/; Dockerfile.dockerignore đi cùngfile, allowlist chỉ app/proto/corpus/bootstrapcầnthiết, chặn ảnh runtime/data/checkpoint/venv. Không coi benchmarkcũ là số hiện hành; image service đầy đủ chưa build ở đợt này.
- Native start-dev gọi app.script.run_dev quản lý REST+gRPC cùngvòngđời; bind127.0.0.1, kiểmcổng, không tự stop/start sharedDocker. grpc_bind_host mặcđịnh[::] cho container, native launcher injectloopback. Readinesshiện tại xác nhận listener/healthtransport, DB/model/provider cần gate riêng.
- developer_dashboard_enabled mặc định false; `AI_DEVELOPER_DASHBOARD_ENABLED=true` chỉ còn mở route chẩn đoán Vision local (loopback, same-origin). `/dashboard`, `static/index.html` và REST dev `/api/copilot/ask`, `/api/knowledge/ingest`, `/api/system/info` đã bỏ (IPLMS ADR-0050) — dùng trang "Công cụ thử" của AI Console. Nạp bản nháp vẫn dùng UUID ổn định; xuất bản theo cổng hiện hành.
- Vision giữ modular/ONNX/two-line/cropmàugốc/strictclassifier và ngưỡng confidence. HSV/deskew chỉ ở enhancement; màuOptionalNone khi chưa có cropquan sát. Thiếuclassifiermodel→None, không suyprior từbiển. Không đổi proto; màu hiện chỉ fieldREST bổsung.
- Setup không tự càiCUDA; không dùng checkpointngẫu nhiên làm model đãtrain. Realmodelaccuracy/latency/provider/DBE2E chưa kiểm trong chặng, xem IPLMS ISSUE-124.
