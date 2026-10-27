---
status: canonical
audience: AI coding agents + developers
applies-to: `ai/` — Python service (FastAPI REST + gRPC), ANPR · Forecast · Copilot
verified-against-code: 2026-10-27 — §1, §3–§8 đọc trực tiếp từ `ai/app/`; §2 là khuôn đích theo ADR-0005, lệch còn lại theo dõi ở ISSUE-023
---

# 🧠 AI Conventions — IPLMS

Nhánh và PR theo [Git workflow local](GIT_WORKFLOW.md), hiệu lực 2026-10-15; không đổi tên nhánh cũ.

**[MUST]** Đọc [DESIGN](../../DESIGN.md) cho kiến trúc cụ thể, ma trận base/develop/production và ngoại lệ; [README](../../README.md) chỉ là điểm vào nhanh. Naming chung khi mở từ umbrella: [NAMING_CONVENTIONS](../../../docs/standards/NAMING_CONVENTIONS.md).

Python dùng `snake_case` cho file/hàm, `PascalCase` cho class, `UPPER_SNAKE_CASE` cho hằng và env key. File REST dùng `<domain>_controller.py`; config dùng `<concern>_config.py`. Thêm project độc lập phải có README + DESIGN + conventions liên kết nhau.

Luật viết code cho plane `ai/`. Stack: Python · FastAPI · gRPC · YOLO + EasyOCR · pgvector · Parquet.

> Phân tầng §1 sạch (quét 2026-09-11). Khuôn domain §2 đổi theo [ADR-0005](../projects/adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md) ngày 2026-10-27; code đang được đưa về khuôn trong [ISSUE-023](../projects/issues/10-2026/ISSUE-023-khuon-domain-core/issue.md), chỗ còn lệch liệt kê ở đó.

## 1. Ba tầng — và hướng phụ thuộc

```text
api/          ⟶  core/           ⟶  infra/
(vào/ra)         (nghiệp vụ)        (hệ thống ngoài)
```

| Tầng | Chứa gì | Được import |
|---|---|---|
| `app/api/` | gRPC handler · REST route · mapper · schema | `core/` |
| `app/core/` | domain theo khuôn §2 | `infra/`, `util/`, `config/`; domain khác chỉ qua `__init__` của nó |
| `app/infra/` | pgvector · Parquet · LLM factory + loader prompt | `config/`, `util/` |

- **[NEVER]** `app/core/` import `grpc`, `_pb2`, hay `generated_stubs`. Đã kiểm: **0 chỗ vi phạm**. Giữ vậy — core không được biết nó đang được gọi qua giao thức nào.
- **[NEVER]** `app/api/` import thẳng `engines/`. Đã kiểm: **0 chỗ vi phạm**. Handler/route chỉ gọi `services/`.
- **[MUST]** `core/*/engines/` được phép gọi `app/infra/` (ví dụ `rag_pipeline.py` → `pgvector_client`, `llm_factory`). Đây là chiều đúng.

## 2. Khuôn một domain trong `core/`

Lý do và phương án đã loại: [ADR-0005](../projects/adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md).

**Domain = bounded context, trùng tên gRPC service:** `vision` · `copilot` · `knowledge` · `knowledge_eval` · `forecast` · `dataset` · `model_policy`, cộng `console` (chỉ REST). Năng lực bên trong (`anpr`, `rag`, `dispute`) là **package con**, không phải domain riêng.

```text
app/core/<domain>/
├── __init__.py     public API — api/ và domain khác chỉ import từ đây
├── dtos/           [bắt buộc] kiểu vào/ra
├── engines/        [bắt buộc] thuật toán / model thuần; ≥3 file cùng một năng lực → engines/<năng-lực>/ có façade
├── services/       [bắt buộc] điều phối một lượt use case
├── workflows/      [tuỳ chọn] đồ thị nhiều bước có checkpoint (LangGraph)
├── guardrails/     [tuỳ chọn] luật / regex an toàn cho đầu vào–đầu ra
├── constants.py    [tuỳ chọn] ngưỡng tinh chỉnh chỉ domain này dùng
└── messages.py     [tuỳ chọn] text hiện cho người dùng + marker nhận diện đi kèm
```

- **[NEVER]** tạo thư mục/file ngoài danh sách trên. Cần slot mới thì sửa ADR-0005 trước. `script/check_core_layout.py` kiểm luật này (ISSUE-023).
- **[NEVER]** tạo thư mục rỗng chỉ để đủ khuôn. Domain chưa có DTO/engine thật thì để trống, thêm khi có.
- **[MUST]** Câu trả lời mẫu và marker nhận diện nó nằm **cùng** `messages.py`. Code eval/script nhận diện câu từ chối thì import marker, không tự viết regex riêng.
- **[MUST]** Code dùng chung giữa hai domain ở lại domain sở hữu, domain kia import qua `__init__`. Hằng số dùng ≥2 domain ở gốc `core/constants.py`. Gốc `core/` chỉ có `constants.py` · `enums.py` · `exceptions.py`.

### Không thuộc `core/`

| Thứ | Chỗ đúng |
|---|---|
| Text gửi LLM: system prompt, khuôn user message, JSON schema output | `data/prompts/<tên>/vN.md` (+ `user.md`, `schema.json`); loader ở `app/infra/llm/` |
| Đọc file / DB / lake | `app/infra/` |
| Dữ liệu mẫu, adapter giả | `test/` hoặc `app/script/` |

- **[NEVER]** viết prompt dạng chuỗi trong `.py` (`"""Bạn là…"""`, `INSTRUCTIONS = """…`), kể cả làm fallback. Thiếu file prompt thì khởi động báo lỗi.
- **[MUST]** Sửa nội dung prompt thì tạo `vN+1.md`, không sửa đè bản đang chạy. Telemetry ghi nhãn `<tên>_<version>#<hash8>`. Backend đọc nhãn này qua `promptVersion`, nên **[NEVER]** đổi dạng nhãn.
- **[MUST]** Đổi prompt hoặc guardrail thì chạy lại `app/script/redteam_copilot.py` (IPLMS ADR-0029).

### Public API của domain

`app/core/<domain>/__init__.py` xuất public symbol để `api/` import gọn ở đầu file (`from app.core.<domain> import ...`), không dùng inline import `from app...` trong thân hàm. Ngoại lệ duy nhất: trì hoãn nạp thư viện ML nặng theo §6. Xoá inline import thì phải thêm import ở đầu file (AUDIT-006 A-1: thiếu bước này làm `ExportForConsole`/`GetAcceptPolicy` ném `NameError`).

### Engine ⇄ Service — ranh giới

| | `engines/` | `services/` |
|---|---|---|
| Trả lời | *"tính cái này ra sao?"* | *"một lượt nghiệp vụ gồm những bước nào?"* |
| Ví dụ thật | `anpr_engine` nạp YOLO + EasyOCR rồi đọc biển | `anpr_service`: *"phát hiện biển → OCR → phân loại xe"* |
| Trạng thái | được phép giữ model nạp sẵn ở module scope | **[NEVER]** giữ trạng thái nghiệp vụ giữa các request |

**[GOTCHA]** `knowledge_eval/services/eval_service.py` giữ `_tasks` để task chạy nền không bị thu gom; đây là tham chiếu vòng đời tiến trình, không phải kết quả nghiệp vụ. Kết quả/lượt chạy phải nằm trong DB để replica khác đọc được. Vì vậy dòng **[NEVER]** ở trên áp dụng cho trạng thái **nghiệp vụ**, không cấm tham chiếu task nền có dọn dẹp.

**[MUST]** Engine mới nặng (nạp model) thì viết lazy-load, và đọc kỹ mục §6.

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

`routes/` (endpoint) · `schemas/` (body/response Pydantic) · `middlewares/` · `router.py` (gom route cho cả `api_router` cổng 8000 và `console_router` cổng 8090).

**[MUST]** File REST đặt `<domain>_controller.py`: `anpr_controller.py`, `health_controller.py`. Đổi tên file phải sửa import ở `router.py`; tên file không đổi URL public. Ngoại lệ `health.py` đã được gỡ ngày 2026-10-14.

## 4. Config

`app/config/` chia theo mối quan tâm, mỗi nhóm một file `<concern>_config.py` (xem thư mục để biết danh sách hiện tại; không liệt kê ở đây vì danh sách cũ đã trôi).

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

`anpr/models.py` giữ model ở module scope với cờ `initialized`. Bản cũ bật cờ **trước** khi nạp xong:

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

Script vận hành chạy tay: sinh stub (`compile_proto.py`), smoke check, seed, eval, red-team. Script kiểm repo chạy trong CI (như `check_core_layout.py`) nằm ở `script/` ngoài `app/`.

**[NEVER]** đặt pytest ở đây. **[NEVER]** để service runtime import từ `app/script/`.

## 🔗 Liên quan

- [`../../backend/docs/BACKEND_CONVENTIONS.md`](../../../backend/docs/standards/BACKEND_CONVENTIONS.md) — phía NestJS gọi sang gRPC
- [`../../docs/guides/backend/grpc-nest-python-ai-integration.md`](../../../docs/guides/09-2026/grpc-nest-python-ai-integration.md) — nối NestJS ⇄ Python
- [`../../deployment/README.md`](../../../deployment/README.md) — probe, timeout, build context
