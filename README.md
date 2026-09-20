# 🧠 `ai/` — Dịch vụ ANPR (nhận diện biển số) cho IPLMS

Module **Python độc lập** (ngang hàng `frontend/`, `backend/`): dịch vụ **FastAPI + Docker** xử lý ảnh biển số, chạy xuyên suốt để `backend` gọi ở khâu **check-in / check-out** cổng.

**Nguồn gốc code — đọc trước khi sửa:**
- **Kiến trúc layered** `app/{api,config,core,infra,utils}` + `static/{cropped,original}` — theo một layout ALPR có sẵn, không tự nghĩ ra ở đây.
- **Engine ALPR** (YOLO detect + EasyOCR) ở `app/core/vision/engines/` là **code bên thứ ba bê nguyên vào**, kèm weights `best.pt` — KHÔNG train trong repo này.
- **CNN phân loại ảnh** (`model/architectures/m1`, `model/architectures/m2`) cũng là **code + kiến trúc bên thứ ba**, ở đây dùng làm **tầng phân loại xe (tuỳ chọn)**.

## 📁 Cấu trúc

Layout theo quy chuẩn `api / config / core / infra / utils` —
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
│   │   ├── base_config.py           #   BaseConfig (pydantic-settings, đọc .env)
│   │   ├── server_config.py         #   cổng gRPC/REST, max workers, max message
│   │   ├── vision_config.py         #   YOLO · EasyOCR · CNN phân loại xe
│   │   ├── llm_config.py            #   pgvector DB · embedding · API key
│   │   ├── datalake_config.py       #   kho Parquet cho forecast
│   │   ├── logging_config.py        #   tên logger · level · format
│   │   └── app_config.py            #   AppConfig gộp + get_config() (lru_cache)
│   ├── core/                        # NGHIỆP VỤ — mỗi domain 1 folder
│   │   ├── vision/                  #   dtos/vision_dto.py · engines/ (anpr, classifier) · services/
│   │   ├── copilot/                 #   dtos/copilot_dto.py · engines/rag_pipeline.py · services/
│   │   └── forecast/                #   dtos/forecast_dto.py · engines/occupancy_model.py · services/
│   ├── infra/                       # ADAPTER RA NGOÀI — database/ (pgvector) · datalake/ · llm/
│   ├── utils/                       # logger.py · console.py · file.py · generate_url.py
│   ├── script/                      # compile_proto.py · grpc_smoke_check.py · seed_*.py
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

## ▶️ Chạy (Docker)

```bash
cd ai
docker compose up --build
# health : curl http://localhost:8000/health
# nhận diện: curl -F "file=@xe.jpg" "http://localhost:8000/api/anpr/recognize?lane_id=gate_in_01"
```

Kết quả (`BaseResponse.data[0]` ~ hợp đồng `anpr-pipeline`):
```json
{ "event_id": "evt_...", "lane_id": "gate_in_01", "plate_number": "51H-99999",
  "confidence": 0.7751, "vehicle_type": null,
  "crop_plate_image_url": "/static/cropped/51H-99999_crop.jpg",
  "process_time": 0.42, "timestamp": "2026-07-26T..." }
```

## ▶️ Chạy local (không Docker)

```bash
cd ai && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## ▶️ Chạy gRPC server (backend NestJS gọi vào)

```bash
cd ai
python app/script/compile_proto.py     # sinh stub — bắt buộc chạy trước
python -m app.grpc_server              # lắng nghe [::]:50051
python app/script/grpc_smoke_check.py  # gọi thử cả 5 service
```

Bên backend đặt `AI_GRPC_URL=localhost:50051` (xem `backend/src/infrastructures/Ai/README.md`).

## ✅ Chạy test

```bash
cd ai
python -m unittest discover -s test -t .
```

Dùng `unittest` của thư viện chuẩn — **không thêm dependency nào**, chạy được ngay
sau `pip install -r requirements.txt`. Ai thích pytest thì `pytest test` vẫn chạy
y nguyên vì pytest hiểu test kiểu unittest.

Bộ test cố ý chỉ chạm **logic thuần**, không nạp model, nên xong trong vài mili-giây:

| File | Giữ cho khỏi vỡ điều gì |
|---|---|
| `test_generate_url.py` | Tên file ảnh khoá theo `event_id` — nếu chỉ theo biển số thì mọi xe không đọc được biển ghi đè chung một file |
| `test_enums_match_proto.py` | Enum Python khớp từng chữ với enum trong proto — lệch là mapper ném lỗi giữa request thật |
| `test_vision_mapper.py` | Mapping DTO ↔ protobuf, gồm `crop_image` bytes mà backend cần để lưu ảnh bền |
| `test_plate_text.py` | Chuẩn hoá chuỗi biển số; ghi lại cả hành vi **chưa** chuẩn (thiếu gạch ngang) để đổi là có chủ đích |
| `test_config.py` | Số nhãn khớp số lớp của model; `grpc_max_message_length` khớp phía NestJS |

## ⚙️ Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `AI_LANE_ID` | `gate_in_01` | `lane_id` gắn vào kết quả |
| `AI_VEHICLE_CHECKPOINT` | *(rỗng)* | Bật tầng phân loại xe khi trỏ tới checkpoint CNN đã train loại xe. **Rỗng = tắt** (`vehicle_type = null`). |
| `AI_VEHICLE_MODEL_VERSION` | `v1` | Version bất biến dùng làm thư mục cache artifact |
| `AI_VEHICLE_ARTIFACT_URL` | *(rỗng)* | Signed HTTPS GET URL; khi có giá trị sẽ ưu tiên hơn checkpoint local |
| `AI_VEHICLE_ARTIFACT_SHA256` | *(rỗng)* | SHA-256 bắt buộc khi tải checkpoint từ URL |
| `AI_VEHICLE_MODEL` | `NetV2` | `NetV1`/`NetV2` cho tầng phân loại xe |
| `AI_VEHICLE_LABELS` | `car_sedan,car_suv,motorbike,truck` | Nhãn lớp (theo thứ tự index) |
| `AI_OCR_LANGUAGES` | `en,vi` | Ngôn ngữ EasyOCR, ngăn cách bởi dấu phẩy |
| `AI_YOLO_MODEL_PATH` | `model/artifacts/bootstrap/anpr/best.pt` | Bootstrap YOLO local, tương đối so với `ai/` |
| `AI_YOLO_MODEL_VERSION` | `bootstrap-v1` | Version detector dùng làm khóa cache |
| `AI_YOLO_ARTIFACT_URL` | *(rỗng)* | Signed HTTPS GET URL; khi có giá trị sẽ ưu tiên hơn bootstrap local |
| `AI_YOLO_ARTIFACT_SHA256` | *(rỗng)* | SHA-256 bắt buộc khi tải detector từ URL |
| `AI_MODEL_REGISTRY_CACHE_DIR` | `var/model-cache` | Cache runtime theo `<model>/<version>/<file>` |
| `AI_OBJECT_STORAGE_MAX_ARTIFACT_MB` | `2048` | Chặn tải artifact vượt giới hạn |
| `AI_GRPC_PORT` | `50051` | Cổng gRPC server |
| `AI_DEVICE` | `cpu` | `cpu`/`cuda` |

## 🔗 Nối backend (ĐÃ WIRE)

Backend NestJS đã có sẵn đường nối:
- `AnprProvider` ([backend/src/infrastructures/Anpr](../backend/src/infrastructures/Anpr)) — HTTP client gọi `POST /api/anpr/recognize` (fetch native, có timeout). Bật bằng env `ANPR_ENABLED=true` + `ANPR_SERVICE_URL=http://localhost:8000`.
- Endpoint cổng: `POST /staff/parking-sessions/check-in-anpr` (multipart `file`, query `laneId?`) → `StaffOperationService.staffCheckInFromImage` → nhận diện biển số qua service này → chạy `staffCheckIn` bình thường (giữ nguyên access-control, nhận diện là bước tiền xử lý tách rời — đúng skill `anpr-pipeline`).

## 📖 Huấn luyện & xem model

Xem [`training/README.md`](training/README.md) — cách chuẩn bị dữ liệu, train NetV1/NetV2, xem checkpoint/log, đếm FLOPs, và cách bật tầng phân loại xe.

## ⚠️ Trung thực về hiện trạng
- **Chỉ ANPR là thật.** Anti-fraud / Forecast / Copilot đều trả `UNIMPLEMENTED` thay vì số bịa — xem `core/*/services/*.py`.
- **Engine ALPR (YOLO+OCR) là thật** — code + weights `best.pt` bê từ bên thứ ba, không train ở đây.
- **`confidence` là số THẬT** (detector × OCR) từ ISSUE-003; `0.0` nghĩa là không đọc được biển, [NEVER] hiểu là "tin 0%".
- **`vehicle_type` mặc định `null`**: checkpoint CNN hiện có train trên CIFAR/Animal-10, **chưa** phân loại xe; chỉ bật khi cấp checkpoint train trên loại xe (`AI_VEHICLE_CHECKPOINT`).
- Model production nên nằm trong object storage private. Service nhận signed URL ngắn hạn, bắt buộc kiểm SHA-256 và chỉ nạp file đã cache thành công; URL không được ghi log.
- **Chưa cài gói** (luật supply-chain): torch/ultralytics/easyocr/opencv là thư viện phổ biến; tự `pip install`. `easyocr` tải model ~vài trăm MB lần chạy đầu.
