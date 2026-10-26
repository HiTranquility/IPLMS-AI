# `app/` — mã dịch vụ AI

Ba process dùng chung code này, mỗi process một điểm vào:

| Điểm vào | Process | Cổng |
|---|---|---|
| `main.py` | REST FastAPI (inference: ANPR, Copilot, Forecast, health) | 8000, sau gateway |
| `grpc_server.py` | gRPC cho backend NestJS | 50051, sau gateway |
| `console_main.py` | AI Console (API `/console/api` + phục vụ `ui/dist`) | 8090, chỉ `127.0.0.1` |

`console_main` **[NEVER]** gắn vào `main.py`: tải của người dùng console không được chạm cổng inference (IPLMS ADR-0048).

## Phân tầng

```text
api/      nhận request, kiểm quyền, đổi DTO ↔ proto/JSON     — không chứa nghiệp vụ
  └─ core/   nghiệp vụ theo domain: services → engines/dtos  — không import FastAPI/gRPC
       └─ infra/  DB, pgvector, LLM, embedding, OCR, storage   — không biết domain
config/   đọc biến môi trường (pydantic-settings), mỗi nhóm một file
util/     logger, metric request, tiện ích file/URL
script/   lệnh vận hành chạy tay: python -m app.script.<tên>
```

Luật import và naming đầy đủ: [AI_CONVENTIONS](../docs/standards/AI_CONVENTIONS.md).

## `api/`

- `rest/routes/*_controller.py`: router REST, gắn dưới `/api` (và gốc) trong `main.py`. Controller `console_*` gắn dưới `/console/api` trong `console_main.py`.
- `rest/console_access.py`: `require_permission` / `require_any_permission` cho Console; ma trận quyền ở `core/console/engines/access_policy.py`.
- `grpc/handlers/`: một handler mỗi service proto (vision, copilot, knowledge, dataset, forecast, model_policy, knowledge_eval, health); `mappers/` đổi proto ↔ DTO; `interceptors/` log và map lỗi ra mã gRPC.
- Stub sinh từ `proto/` nằm ở `api/grpc/generated/` (không commit): `python app/script/compile_proto.py`.

## `core/`

| Domain | Việc | README |
|---|---|---|
| `vision/` | ANPR: YOLO tìm biển → cắt → OCR → chuẩn hoá biển VN; phân loại xe | [vision](core/vision/README.md) |
| `copilot/` | Hỏi đáp RAG, guardrail, output guard, stream; khung LangGraph phân xử | [copilot](core/copilot/README.md) |
| `knowledge/` | Parse PDF/DOCX/MD, chunk, embed, version bản nháp/xuất bản | [knowledge](core/knowledge/README.md) |
| `knowledge_eval/` | Cổng đánh giá trước khi xuất bản tri thức | [knowledge_eval](core/knowledge_eval/README.md) |
| `dataset/` | Gom, gán nhãn, snapshot dữ liệu train/golden | [dataset](core/dataset/README.md) |
| `forecast/` | Dự báo lấp đầy từ datalake Parquet (chưa bật phục vụ) | [forecast](core/forecast/README.md) |
| `model_policy/` | Hồ sơ model/prompt theo task, có revision | — |
| `console/` | Nghiệp vụ AI Console: đăng nhập, thành viên, audit, Copilot Lab, Vision Lab, công cụ | — |

`constants.py`, `enums.py`, `exceptions.py` dùng chung giữa các domain; enum phải khớp proto (`test/test_enums_match_proto.py`).

## `infra/`

`database/` (pgvector, store của console, log request) · `embedding/` · `llm/` (`LlmFactory`: OpenAI, Ollama, llama-server; `generate_json` cho structured output) · `ocr/` · `storage/`, `model_registry/` (artifact có SHA-256) · `datalake/` · `monitoring/` (telemetry token, độ trễ, chi phí) · `identity/` (Google OIDC) · `workflow/` (checkpoint LangGraph).

## `script/` hay dùng

| Lệnh | Làm gì |
|---|---|
| `python -m app.script.console_admin --email … --display-name …` | Tạo admin khẩn cấp của Console |
| `python -m app.script.seed_console_demo` | Nạp dữ liệu demo cho Console (cần `AI_CONSOLE_DEMO_SEED_ENABLED=true`) |
| `python -m app.script.ingest_knowledge` | Nạp tài liệu tri thức |
| `python -m app.script.eval_ai_engineering` | Chạy bộ eval RAG |
| `python -m app.script.eval_copilot_e2e` | Đo ngưỡng similarity với model embedding đang dùng |
| `python -m app.script.redteam_copilot` | Bộ tấn công prompt injection / ngoài phạm vi |
| `python app/script/compile_proto.py` | Sinh stub gRPC |
| `python -m app.script.harden_console_db` | Siết quyền DB console |
