# 🧠 `ai/` — Dịch vụ ANPR (nhận diện biển số) cho IPLMS

Module **Python độc lập** (ngang hàng `frontend/`, `backend/`): dịch vụ **FastAPI + Docker** xử lý ảnh biển số, chạy xuyên suốt để `backend` gọi ở khâu **check-in / check-out** cổng.

**Nguồn gốc code — đọc trước khi sửa:**
- **Kiến trúc layered** `app/{api,config,core,infra,util}` + `static/{cropped,original}` — theo một layout ALPR có sẵn, không tự nghĩ ra ở đây.
- **Engine ALPR** (YOLO detect + EasyOCR) ở `app/core/vision/engines/` là **code bên thứ ba bê nguyên vào**, kèm weights `best.pt` — KHÔNG train trong repo này.
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
│   │       └── routes/              #     anpr_controller.py · health.py
│   ├── config/                      # CẤU HÌNH — mỗi nhóm 1 file, gom ở app_config.get_config()
│   │   ├── base_config.py           #   BaseConfig (pydantic-settings, native dev đọc .env.dev)
│   │   ├── server_config.py         #   cổng gRPC/REST, max workers, max message
│   │   ├── vision_config.py         #   YOLO · EasyOCR · CNN phân loại xe
│   │   ├── llm_config.py            #   pgvector DB · embedding · API key
│   │   ├── datalake_config.py       #   export batch + slot occupancy cho forecast
│   │   ├── logging_config.py        #   tên logger · level · format
│   │   └── app_config.py            #   AppConfig gộp + get_config() (lru_cache)
│   ├── core/                        # NGHIỆP VỤ — mỗi domain 1 folder
│   │   ├── vision/                  #   dtos/vision_dto.py · engines/ (anpr, classifier) · services/
│   │   ├── copilot/                 #   dtos/copilot_dto.py · engines/rag_pipeline.py · services/
│   │   └── forecast/                #   dtos/forecast_dto.py · engines/occupancy_model.py · services/
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
├── proto/ → dùng `proto/*.proto` ở GỐC REPO (4 file, nguồn chuẩn dùng chung với backend)
├── Dockerfile · docker-compose.yml · requirements*.txt
```

**Luật tầng:**
- `api/` chỉ điều phối: nhận message → gọi `core/*/services` → `mappers/` dựng protobuf. **Không** nhét nghiệp vụ vào handler.
- `core/*/services` trả **DTO** (pydantic/dataclass), **không** trả `dict` — nhờ vậy mapper và route đều có type.
- Mọi cấu hình đi qua `get_config()`. **Không** `os.getenv` rải rác trong engine/service.
- Đổi hợp đồng → sửa `proto/*.proto` ở gốc repo → chạy lại `compile_proto.py` (và `npm run proto:sync` bên backend).
- Ném exception từ `core/exceptions.py`; `LoggingInterceptor` quy nó về đúng gRPC status. **Không** try/except nuốt lỗi trong handler.

> **Stateless:** dịch vụ này không có tầng DB nghiệp vụ — IPLMS backend giữ DB. `PlateResult` là *domain model* (dataclass), không phải ORM.

## 🔀 Luồng xử lý (services/anpr_service.py)

```
ảnh cổng ──► run_alpr (app/core/vision/engines/alpr_engine)
                 ├─ YOLO (best.pt) phát hiện + crop biển
                 └─ EasyOCR đọc ký tự (đa tầng fallback: full → crop → enhanced)
             ──► classify_vehicle (CNN, optional) ─────► vehicle_type
             ──► lưu ảnh gốc + crop vào static/
             ──► PlateResult {plate_number, vehicle_type, crop_url, process_time, ...}
```

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

> **Lưu ý Full-stack:** Nếu chạy toàn bộ hệ thống cùng backend, dùng `deployment/script/run-stack.ps1` (hoặc `.sh`). AI sẽ chạy cùng mạng nội bộ `iplms-backend-dev_default` với PostgreSQL, Redis, Keycloak.

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
- Forecast: [export session thật → readiness → baseline backtest theo lot/horizon](docs/guides/04-forecast-training-strategy.md#quy-trình-chạy-thật-từ-postgresql-đến-baseline-report).
- Notebook Forecast: [`notebook/forecast_experiment.ipynb`](notebook/forecast_experiment.ipynb) chỉ điều phối readiness và runner; không chứa logic train.
- Upload ảnh và đo request gRPC/REST: [guide Postman](../docs/guides/backend/test-grpc-ai-with-postman.md).

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
| `AI_LLM_API_KEY` | *(rỗng)* | OpenAI API key cho Copilot và Embedding |
| `AI_LLM_MODEL` | `gpt-5.6-luna` | Model LLM sinh câu trả lời |
| `AI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model sinh vector cho tri thức |
| `AI_RAG_TOP_K` | `5` | Số chunk tương đồng lấy từ pgvector |
| `AI_RAG_MIN_SIMILARITY` | `0.35` | Ngưỡng tương đồng cosine tối thiểu |
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
