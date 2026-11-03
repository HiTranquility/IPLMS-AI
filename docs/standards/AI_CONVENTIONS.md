---
status: canonical
audience: AI coding agents + developers
applies-to: `ai/` — Python service (FastAPI REST + gRPC), ANPR · Forecast · Copilot
verified-against-code: 2026-11-03 — đọc trực tiếp từ `ai/app/`; §2 kiểm bằng `script/check_core_layout.py` (0 lệch), §9 kiểm bằng `test/test_logging_interceptor.py`
---

# 🧠 AI Conventions — IPLMS

Nhánh và PR theo [Git workflow local](GIT_WORKFLOW.md), hiệu lực 2026-10-15; không đổi tên nhánh cũ.

**[MUST]** Đọc [DESIGN](../../DESIGN.md) cho kiến trúc cụ thể, ma trận base/develop/production và ngoại lệ; [README](../../README.md) chỉ là điểm vào nhanh. Naming chung khi mở từ umbrella: [NAMING_CONVENTIONS](../../../docs/standards/NAMING_CONVENTIONS.md).

Python dùng `snake_case` cho file/hàm, `PascalCase` cho class, `UPPER_SNAKE_CASE` cho hằng và env key. File REST dùng `<domain>_controller.py`; config dùng `<concern>_config.py`. Thêm project độc lập phải có README + DESIGN + conventions liên kết nhau.

Luật viết code cho plane `ai/`. Stack: Python · FastAPI · gRPC · YOLO + EasyOCR · pgvector · Parquet.

> Phân tầng §1 sạch (quét 2026-09-11). Khuôn domain §2 đổi theo [ADR-0005](../projects/adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md) ngày 2026-10-27; code đưa về khuôn trong [ISSUE-023](../projects/issues/10-2026/ISSUE-023-khuon-domain-core/issue.md) (2026-10-28); ngoại lệ còn lại ghi trong bảng "Không thuộc `core/`".

## 1. Ba tầng — và hướng phụ thuộc

```text
api/          ⟶  core/           ⟶  infra/
(vào/ra)         (nghiệp vụ)        (hệ thống ngoài)
```

| Tầng | Chứa gì | Được import |
|---|---|---|
| `app/api/` | gRPC handler · REST route · mapper · schema | `core/` |
| `app/core/` | domain theo khuôn §2 | `infra/`, `util/`, `config/`; domain khác chỉ qua `__init__` của nó |
| `app/infra/` | pgvector · Parquet · LLM factory + loader prompt · embedding · storage · ocr | `config/`, `util/`, `core.exceptions` (ngoại lệ hợp thức: ném lỗi nghiệp vụ chuẩn để interceptor gRPC quy đổi status theo §9) |

- **[NEVER]** `app/core/` import `grpc`, `_pb2`, hay `generated_stubs`. Đã kiểm: **0 chỗ vi phạm**. Giữ vậy — core không được biết nó đang được gọi qua giao thức nào.
- **[NEVER]** `app/api/` import thẳng `engines/`. Đã kiểm: **0 chỗ vi phạm**. Handler/route chỉ gọi `services/`.
- **[MUST]** `core/*/engines/` được phép gọi `app/infra/` (ví dụ `rag_pipeline.py` → `pgvector_client`, `llm_factory`). Đây là chiều đúng.

## 2. Khuôn một domain trong `core/`

Lý do và phương án đã loại: [ADR-0005](../projects/adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md).

**Domain = bounded context, trùng tên gRPC service:** `vision` · `copilot` · `knowledge` · `knowledge_eval` · `forecast` · `dataset` · `model_policy`, cộng `console` (chỉ REST). Năng lực bên trong (`anpr`, `rag`, `dispute`) là **package con**, không phải domain riêng.

| Domain | Cổng phục vụ | `dtos/` | `engines/` | `services/` | Slot tuỳ chọn (`workflows/` · `guardrails/` · `constants.py` · `messages.py`) |
|---|---|---|---|---|---|
| `vision` | gRPC `VisionService` + REST `/api/v1/anpr` | `vision_dto.py` | `anpr/`, `vehicle_classifier.py` | `anpr_service.py`, `anti_fraud_service.py` | `constants.py`, `README.md` |
| `copilot` | gRPC `CopilotService` + REST `/api/v1/copilot` | `copilot_dto.py` | `rag_pipeline.py` | `copilot_service.py`, `usage_service.py` | `workflows/dispute/` (`state.py`, `nodes.py`, `graph.py`), `guardrails/` (`guardrail_manager.py`, `output_guard.py`, `pii_redactor.py`, `text_normalize.py`), `messages.py`, `README.md` |
| `knowledge` | gRPC `KnowledgeService` + REST `/api/v1/knowledge` | `knowledge_dto.py` | `chunker.py`, `document_parser.py` | `ingestion_service.py` | `guardrails/injection_scan.py`, `constants.py` |
| `knowledge_eval` | gRPC `KnowledgeEvalService` | `eval_dto.py` | `case_generator.py`, `gate.py`, `grader.py`, `judge.py` | `eval_service.py` | `README.md` |
| `forecast` | gRPC `ForecastService` + REST `/api/v1/forecast` | `forecast_dto.py` | `baseline_forecaster.py`, `lake_forecaster.py`, `pricing_advisor.py` | `forecast_service.py` | `constants.py`, `README.md` |
| `dataset` | gRPC `DatasetService` | `sample_dto.py` | `image_quality.py`, `plate_metrics.py`, `sample_selector.py` | `curation_service.py`, `eval_service.py`, `snapshot_service.py` | `README.md` |
| `model_policy` | gRPC `ModelPolicyService` | `model_policy_dto.py` (`ModelProfileDraft`) | `validation.py` | `model_policy_service.py` | — |
| `console` | REST `:8090` (`/console/api/*`) | `console_dto.py` (`ConsoleActor`, `ConsoleSession`, `ExportedCapture`) | `access_policy.py`, `audit_accuracy.py`, `demo_plate_generator.py`, `rate_limiter.py`, `session_policy.py` | `accept_policy_service.py`, `auth_service.py`, `copilot_lab_service.py`, `member_service.py`, `model_connection_service.py`, `model_lab_service.py`, `tools_service.py`, `vision_import_service.py`, `vision_lab_service.py` | `guardrails/model_endpoint.py` |

```text
app/core/<domain>/
├── __init__.py     public API — api/ và domain khác chỉ import từ đây
├── dtos/           [bắt buộc] kiểu vào/ra
├── engines/        [bắt buộc] thuật toán / model thuần; ≥3 file cùng một năng lực → engines/<năng-lực>/ có façade
├── services/       [bắt buộc] điều phối một lượt use case
├── workflows/      [tuỳ chọn] đồ thị nhiều bước có checkpoint (LangGraph)
├── guardrails/     [tuỳ chọn] luật / regex an toàn cho đầu vào–đầu ra
├── constants.py    [tuỳ chọn] hằng số chỉ domain này dùng
├── messages.py     [tuỳ chọn] text hiện cho người dùng
└── README.md       [tuỳ chọn] sơ đồ và mô tả domain
```

- **[NEVER]** tạo thư mục/file ngoài danh sách trên. Cần slot mới thì sửa ADR-0005 trước. CI chạy `script/check_core_layout.py` để kiểm.
- **[NEVER]** tạo thư mục rỗng chỉ để đủ khuôn. Domain chưa có DTO/engine thật thì để trống, thêm khi có.
- **[MUST]** DTO khai báo trong `dtos/<tên>_dto.py` (không khai báo `class` trực tiếp trong `dtos/__init__.py` hay `@dataclass` trong `services/`). Mỗi file trong `services/` đặt tên `<stem>_service.py`, khai báo `class <Stem>Service` (PascalCase khớp `<stem>_service`, không lặp tiền tố domain) và singleton `<stem>_service = <Stem>Service()`. `services/__init__.py` chỉ giữ docstring để không che submodule `app.core.<domain>.services.<stem>_service`; public API xuất ở `<domain>/__init__.py`.
- **[MUST]** Hằng số dùng ≥2 domain ở gốc `core/constants.py`; hằng chỉ một domain dùng ở `<domain>/constants.py`; ngưỡng riêng một module giữ cạnh code dùng nó. Gốc `core/` chỉ có `constants.py` · `enums.py` · `exceptions.py`.
- **[MUST]** Code dùng chung giữa hai domain ở lại domain sở hữu, domain kia import qua `__init__`.
- **[GOTCHA]** Import bất kỳ module nào trong một domain (kể cả `messages.py`) là chạy `__init__.py` của domain đó, kéo cả service và thư viện nặng (copilot ~2,3 s). Module cần nhẹ (như `knowledge_eval/engines/grader.py`, chỉ dùng stdlib) thì không import chéo domain. Muốn ràng buộc thì dùng test hợp đồng. Ví dụ: marker câu từ chối ở `grader.py`, và `test_knowledge_eval.py` kiểm nó nhận ra `copilot.messages.NO_CONTEXT_ANSWER`.

### Không thuộc `core/`

| Thứ | Chỗ đúng |
|---|---|
| Text gửi LLM: system prompt, khuôn user message, JSON schema output | `data/prompts/<tên>/vN.md` (+ `user.md`, `schema.json`), nạp qua `prompt_store` (`app/infra/llm/prompts.py`) |
| Đọc file / DB / lake | `app/infra/` (Parquet occupancy: `infra/datalake/parquet_occupancy_store.py`) |
| Dữ liệu mẫu, adapter giả | `test/` hoặc `app/script/` (ngoại lệ: `copilot/workflows/dispute/fixtures.py` khi workflow chưa nối backend; `console/engines/demo_plate_generator.py` sinh ảnh biển số mẫu cho sandbox khi bật `demo_seed_enabled`) |

Hiện có: `copilot_rag_system` (Copilot), `eval_judge`, `eval_generator` (knowledge_eval), `redteam_attacker` (LLM tấn công của `app/script/redteam_agent.py`).

- **[NEVER]** viết prompt dạng chuỗi trong `.py` (`"""Bạn là…"""`, `INSTRUCTIONS = """…`), kể cả làm fallback. Thiếu file prompt thì khởi động báo lỗi.
- **[MUST]** Sửa nội dung prompt thì tạo `vN+1.md` (bản số lớn nhất tự được dùng), không sửa đè bản đang chạy. Telemetry ghi nhãn `<tên>_<version>#<hash8>`. Backend đọc nhãn này qua `promptVersion`, nên **[NEVER]** đổi dạng nhãn.
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

**[MUST]** Mapper đặt tên theo chiều: `to_<dto>_command` / `to_<dto>_query` cho chiều vào (proto → DTO/domain), `to_<...>_response` cho chiều ra (DTO/domain → proto) — áp dụng thống nhất trên cả 7 mapper (`vision`, `copilot`, `knowledge`, `knowledge_eval`, `forecast`, `dataset`, `model_policy`). Ngoại lệ: message từng khung của server-streaming đặt `to_*_event` (`to_progress_event`, `to_result_event`) hoặc `to_answer_chunk`.
**[NEVER]** sửa tay file trong `generated/`. Sinh lại bằng `app/script/compile_proto.py`.

### REST

`routes/` (endpoint) · `schemas/` (body/response Pydantic) · `middlewares/` · `router.py` (gom route cho cả `api_router` cổng 8000 và `console_router` cổng 8090).

**[MUST]** File REST đặt `<domain>_controller.py`: `anpr_controller.py`, `health_controller.py`. Đổi tên file phải sửa import ở `router.py`; tên file không đổi URL public. Ngoại lệ `health.py` đã được gỡ ngày 2026-10-14.
**[MUST]** Mọi Pydantic request/response model (`BaseModel`) của REST đặt tại `app/api/rest/schemas/<domain>_schema.py`, **[NEVER]** khai báo class `BaseModel` trực tiếp bên trong `app/api/rest/routes/*_controller.py`.

## 4. Config

`app/config/` chia theo mối quan tâm, mỗi nhóm một file `<concern>_config.py` được gom tại `app_config.py` (`AppConfig`):
- `server_config.py`, `vision_config.py`, `llm_config.py`, `embedding_config.py`, `datalake_config.py`, `logging_config.py`, `model_registry_config.py`, `object_storage_config.py`, `workflow_config.py`, `eval_config.py`, `console_config.py`, `telemetry_config.py`, và `runtime_override_config.py`.

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

`anpr/model_loader.py` giữ model ở module scope với cờ `initialized`. Bản cũ bật cờ **trước** khi nạp xong:

> *"Bật trước (bản cũ) khiến request thứ hai đi tiếp với reader vẫn là None → FAILED_PRECONDITION ngay sau mỗi lần restart pod."*

**[MUST]** Lazy-load model thì: khoá bằng `threading.Lock()`, và bật cờ `initialized` **SAU** khi nạp xong — không bao giờ trước.

**[GOTCHA]** Request ANPR đầu tiên sau restart mất ~19–24s để nạp EasyOCR + YOLO. Vì vậy `AI_GRPC_TIMEOUT_MS=30000`, **[NEVER]** hạ xuống dưới 25s (xem `deployment/README.md` §6).

## 7. Build image — context là **chính repo AI**

Theo [ADR-0006](../projects/adrs/10-2026/0006-build-context-la-repo-ai.md), `Dockerfile` chỉ COPY trong repo này, kể cả `proto/` (bản chép của `IPLMS/proto/`):

```bash
docker build -t iplms-ai:latest .            # ✅ từ gốc repo AI (clone riêng hoặc ai/ trong umbrella)
docker build -f ai/Dockerfile .              # ❌ context umbrella cũ — COPY không còn tiền tố ai/
```

**[MUST]** Đổi hợp đồng gRPC: sửa `IPLMS/proto/` → chép sang `proto/` của repo này trong cùng đợt → `IPLMS/proto/check_proto_sync.py` phải xanh. **[MUST]** Thêm file cần vào image thì mở trong allowlist `.dockerignore`.

## 8. `app/script/` — chạy tay, không phải test

Script vận hành chạy tay: sinh stub (`compile_proto.py`), smoke check, seed, eval, red-team. Script kiểm repo chạy trong CI (như `check_core_layout.py`) nằm ở `script/` ngoài `app/`.

**[NEVER]** đặt pytest ở đây. **[NEVER]** để service runtime import từ `app/script/`.

## 9. Bảng quy đổi lỗi → gRPC status

Mọi exception nghiệp vụ kế thừa `AiServiceError` (`app/core/exceptions.py`) và được quy đổi tập trung tại `app/api/grpc/interceptors/logging_interceptor.py` (`_STATUS_BY_EXCEPTION`):

| Nhóm lỗi | Exception | gRPC Status | Hành vi phía Backend (`BaseAiProvider`) |
|---|---|---|---|
| Dữ liệu đầu vào sai | `InvalidImageError`, `UnsupportedFormatError`, `NoTextLayerError`, `DocumentTooLargeError`, `WorkflowStateError`, `ValueError` | `INVALID_ARGUMENT` | Trả 400 Bad Request kèm message cho client |
| Không tìm thấy kết quả | `PlateRecognitionError` | `NOT_FOUND` | Trả 404 / xử lý "không nhận ra biển" |
| Xác thực / quyền / tốc độ Console | `ConsoleAuthError`, `ConsoleAccessDenied`, `ConsoleRateLimited` | `UNAUTHENTICATED` / `PERMISSION_DENIED` / `RESOURCE_EXHAUSTED` | Trả 401 / 403 / 429 |
| Cổng nghiệp vụ / cấu hình chưa sẵn sàng | `FraudDetectedError`, `ModelNotLoadedError`, `KnowledgeGateError`, `ModelConfigurationError`, `WorkflowConfigurationError` | `FAILED_PRECONDITION` | Giữ nguyên message nghiệp vụ/cấu hình trả về người dùng (không retry mù) |
| Hạ tầng phía sau tạm sập | `EmbeddingError`, `RagPipelineError`, `DataLakeError`, `ConsoleStoreError` | `UNAVAILABLE` | Báo `AI_UNAVAILABLE` (503), không ngụy trang thành "chưa tìm thấy thông tin" (`NO_CONTEXT`) |
| Chưa triển khai thật | `FeatureNotImplementedError` | `UNIMPLEMENTED` | Báo 501, tuyệt đối không bịa số liệu |

- **[MUST]** Thêm lớp con `AiServiceError` mới trong `app/core/exceptions.py` thì bắt buộc khai báo trong `_STATUS_BY_EXCEPTION` (`test/test_logging_interceptor.py` kiểm tự động 100% subclass).

## 10. Kiểm thử (Testing)

- Toàn bộ unit test và contract test đặt tại `test/test_*.py`, chạy bằng `python -m unittest discover -s test` (hoặc `pytest`).
- Test cần tài nguyên ngoài (Postgres thật, OCR PDF, model nặng) dùng `@unittest.skipUnless(...)` theo biến môi trường (`AI_TEST_DATABASE_URL`, `AI_TEST_OCR=1`), không được làm đỏ CI khi chạy offline.
- Đổi guardrail, prompt hoặc RAG pipeline phải chạy bộ đánh giá `python -X utf8 app/script/eval_ai_engineering.py --copilot-only` và đảm bảo các ca `test/test_eval_set.py` + `test/test_copilot_eval_dataset.py` xanh.

## 🔗 Liên quan

- [`../../backend/docs/BACKEND_CONVENTIONS.md`](../../../backend/docs/standards/BACKEND_CONVENTIONS.md) — phía NestJS gọi sang gRPC
- [`../../docs/guides/backend/grpc-nest-python-ai-integration.md`](../../../docs/guides/09-2026/grpc-nest-python-ai-integration.md) — nối NestJS ⇄ Python
- [`../../deployment/README.md`](../../../deployment/README.md) — probe, timeout, build context
