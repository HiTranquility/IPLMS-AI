---
status: canonical
audience: AI coding agents + developers
applies-to: `ai/` — Python service (FastAPI REST + gRPC), ANPR · Forecast · Copilot
verified-against-code: 2026-09-11 — mọi đường dẫn, tên file, hướng import dưới đây đọc trực tiếp từ `ai/app/`
---

# 🧠 AI Conventions — IPLMS

Luật viết code cho plane `ai/`. Stack: Python · FastAPI · gRPC · YOLO + EasyOCR · pgvector · Parquet.

> Kiến trúc hiện tại **sạch** — quét ngày 2026-09-11 không thấy vi phạm phân tầng nào.
> Tài liệu này chốt lại cái đang đúng để nó không trôi, chứ không đề xuất đổi gì.

## 1. Ba tầng — và hướng phụ thuộc

```text
api/          ⟶  core/           ⟶  infra/
(vào/ra)         (nghiệp vụ)        (hệ thống ngoài)
```

| Tầng | Chứa gì | Được import |
|---|---|---|
| `app/api/` | gRPC handler · REST route · mapper · schema | `core/` |
| `app/core/` | `dtos/` `engines/` `services/` theo từng domain | `infra/`, `util/`, `config/` |
| `app/infra/` | pgvector · Parquet · LLM factory | `config/`, `util/` |

- **[NEVER]** `app/core/` import `grpc`, `_pb2`, hay `generated_stubs`. Đã kiểm: **0 chỗ vi phạm**. Giữ vậy — core không được biết nó đang được gọi qua giao thức nào.
- **[NEVER]** `app/api/` import thẳng `engines/`. Đã kiểm: **0 chỗ vi phạm**. Handler/route chỉ gọi `services/`.
- **[MUST]** `core/*/engines/` được phép gọi `app/infra/` (ví dụ `rag_pipeline.py` → `pgvector_client`, `llm_factory`; `occupancy_model.py` → `parquet_reader`). Đây là chiều đúng.

## 2. Mỗi domain trong `core/` có đúng ba thư mục

Cả ba domain hiện tại đều theo khuôn này — **[MUST]** domain mới cũng vậy:

```text
app/core/<domain>/
├── dtos/        kiểu vào/ra của domain
├── engines/     thuật toán / model thuần
└── services/    điều phối một lượt use case
```

| Domain | engines | services |
|---|---|---|
| `vision` | `anpr_engine.py` · `vehicle_classifier.py` | `anpr_service.py` · `anti_fraud_service.py` |
| `forecast` | `occupancy_model.py` | `forecast_service.py` |
| `copilot` | `rag_pipeline.py` | `copilot_service.py` |

### Engine ⇄ Service — ranh giới

| | `engines/` | `services/` |
|---|---|---|
| Trả lời | *"tính cái này ra sao?"* | *"một lượt nghiệp vụ gồm những bước nào?"* |
| Ví dụ thật | `anpr_engine` nạp YOLO + EasyOCR rồi đọc biển | `anpr_service`: *"phát hiện biển → OCR → phân loại xe"* |
| Trạng thái | được phép giữ model nạp sẵn ở module scope | **[NEVER]** giữ trạng thái giữa các request |

**[MUST]** Engine mới nặng (nạp model) thì viết lazy-load, và đọc kỹ mục §6.

Dùng chung cho mọi domain, đặt ở gốc `app/core/`: `constants.py` · `enums.py` · `exceptions.py`.
**[NEVER]** khai hằng số dùng-nhiều-domain bên trong một domain.

## 3. Hai cổng vào, **một** đường nghiệp vụ

gRPC và REST là hai vỏ của **cùng** service — đã kiểm: `anpr_controller.py` (REST) và `vision_handler.py` (gRPC) cùng import `AnprService`.

```text
api/grpc/handlers/vision_handler.py ─┐
                                     ├─→ core/vision/services/anpr_service.py
api/rest/routes/anpr_controller.py  ─┘
```

**[NEVER]** viết lại logic cho riêng một cổng. Thấy REST và gRPC cho kết quả khác nhau ⇒ có người đã chép logic.

### gRPC

| Thư mục | Vai trò |
|---|---|
| `handlers/` | `class <Domain>Handler(_pb2_grpc.<Domain>ServiceServicer)` — nhận message, gọi mapper, gọi service |
| `mappers/` | protobuf ⇄ DTO, **cả hai chiều** |
| `interceptors/` | cắt ngang (hiện có `logging_interceptor.py`) |
| `generated/`, `generated_stubs.py` | stub sinh tự động |

**[MUST]** Mapper đặt tên theo chiều: `to_<dto>_command` / `to_<dto>_query` cho chiều vào, `to_<...>_response` cho chiều ra — đúng như `vision_mapper.py` đang làm.
**[NEVER]** sửa tay file trong `generated/`. Sinh lại bằng `app/script/compile_proto.py`.

### REST

`routes/` (endpoint) · `schemas/` (body/response Pydantic) · `middlewares/` · `router.py` (gom route).

**[GOTCHA] Đang có lệch tên:** `routes/` chứa `anpr_controller.py` và `health.py` — một cái có hậu tố `_controller`, một cái không. **[MUST]** file mới đặt `<domain>_controller.py`; `health.py` là ngoại lệ lịch sử, đổi tên nó thì phải sửa `router.py`.

## 4. Config

`app/config/` chia theo mối quan tâm: `app_config` · `base_config` · `datalake_config` · `llm_config` · `logging_config` · `model_registry_config` · `object_storage_config` · `server_config` · `vision_config`.

- **[MUST]** đọc config qua `from app.config import get_config`. **[NEVER]** đọc `os.environ` rải rác trong engine/service.
- **[MUST]** thêm nhóm cấu hình mới = thêm **một file** trong `app/config/`, không nhét vào `app_config.py`.

## 5. Hai file `requirements` — đừng nhầm

| File | Dùng khi | Khác biệt |
|---|---|---|
| `requirements.txt` | dev máy cá nhân | đủ bộ, gồm cả `training/`, torch bản đầy đủ |
| `requirements-service.txt` | **build Docker image** | `--extra-index-url .../whl/cpu` → torch CPU, image nhỏ hơn nhiều |

- **[MUST]** thêm dependency mà service runtime cần ⇒ thêm vào **cả hai**.
- **[MUST]** thêm dependency chỉ phục vụ training/eval ⇒ **chỉ** `requirements.txt`.
- **[NEVER]** đưa torch bản CUDA vào `requirements-service.txt`.

## 6. [GOTCHA] Nạp model — cái bẫy đã cắn một lần

`anpr_engine.py` giữ model ở module scope với cờ `initialized`. Bản cũ bật cờ **trước** khi nạp xong:

> *"Bật trước (bản cũ) khiến request thứ hai đi tiếp với reader vẫn là None → FAILED_PRECONDITION ngay sau mỗi lần restart pod."*

**[MUST]** Lazy-load model thì: khoá bằng `threading.Lock()`, và bật cờ `initialized` **SAU** khi nạp xong — không bao giờ trước.

**[GOTCHA]** Request ANPR đầu tiên sau restart mất ~19–24s để nạp EasyOCR + YOLO. Vì vậy `AI_GRPC_TIMEOUT_MS=30000`, **[NEVER]** hạ xuống dưới 25s (xem `deployment/README.md` §6).

## 7. Build image — context là **gốc repo**

`ai/Dockerfile` cần `proto/` nằm ngoài `ai/`, nên:

```bash
docker build -f ai/Dockerfile .      # ✅ context = gốc repo
docker build ai/                     # ❌ không có proto/ → không sinh được stub
```

## 8. `app/script/` — chạy tay, không phải test

`compile_proto.py` (sinh stub) · `grpc_smoke_check.py` (gọi thử 5 gRPC service) · `seed_regulations.py` · `seed_datalake_logs.py`.

**[NEVER]** đặt pytest ở đây. **[NEVER]** để service runtime import từ `app/script/`.

## 🔗 Liên quan

- [`../../backend/docs/BACKEND_CONVENTIONS.md`](../../backend/docs/BACKEND_CONVENTIONS.md) — phía NestJS gọi sang gRPC
- [`../../docs/guides/backend/grpc-nest-python-ai-integration.md`](../../docs/guides/backend/grpc-nest-python-ai-integration.md) — nối NestJS ⇄ Python
- [`../../deployment/README.md`](../../deployment/README.md) — probe, timeout, build context
