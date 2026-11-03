# 🏷️ ISSUE-027: Đồng nhất quy ước đặt tên và bố cục trên `app/core/`, `app/infra/`, `app/api/rest/` (ADR-0005 & AI_CONVENTIONS)

> **Đích:** `docs/projects/issues/11-2026/ISSUE-027-core-naming-consistency/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Done |
| **Người nhận** | @HiTranquility |
| **Ngày tạo** | 2026-11-03 |
| **Hạn** |  |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** | 2026-11-03 |
| **Người phụ trách** | HiTranquility |
| **Phạm vi** | IPLMS-AI: `app/core/**`, `app/infra/**`, `app/api/**`, `app/script/**`, `training/`, `benchmark/`, `test/`, `script/check_core_layout.py`, `docs/projects/adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md`, `docs/standards/AI_CONVENTIONS.md` |

## Mục tiêu

Tiếp nối [ISSUE-023](../../10-2026/ISSUE-023-khuon-domain-core/issue.md) và [ADR-0005](../../../adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md): đồng nhất cách đặt tên và bố cục trên toàn bộ `app/core/`, `app/infra/`, `app/api/rest/` và bổ sung kiểm tự động trong `script/check_core_layout.py`.

## Các thay đổi đã thực hiện

1. **Quy ước `services/<stem>_service.py` thống nhất trên cả 8 domain (`app/core/`):**
   - Mỗi file `<stem>_service.py` khai báo `class <Stem>Service` (PascalCase khớp tên file, bỏ tiền tố domain thừa: `Console*Service` → `*Service`, `CopilotUsageService` → `UsageService`, `KnowledgeEvalService` → `EvalService`) và singleton `<stem>_service = <Stem>Service()`.
   - Bổ sung singleton còn thiếu ở `dataset` (`curation_service`, `snapshot_service`, `eval_service`) và `vision` (`anpr_service`).
   - `<domain>/services/__init__.py` chỉ giữ docstring để không che submodule `app.core.<domain>.services.<stem>_service`; public API xuất ở `<domain>/__init__.py`.
2. **Chuẩn hoá `dataset/services/evaluation_service.py` → `eval_service.py`:**
   - Đổi tên thành `eval_service.py` (đồng nhất với `knowledge_eval/services/eval_service.py`), gói vào `class EvalService` + `eval_service = EvalService()`.
   - Chuyển DTO `@dataclass EvalSample` sang `dataset/dtos/sample_dto.py`.
3. **Thống nhất `dtos/<tên>_dto.py`:**
   - Tách DTO khai báo trực tiếp trong `__init__.py` sang `console/dtos/console_dto.py` và `model_policy/dtos/model_policy_dto.py`.
4. **Đặt tên rõ nghĩa và ghi nhận ngoại lệ trong `app/core/`:**
   - `vision/engines/anpr/models.py` → `vision/engines/anpr/model_loader.py` (cập nhật luôn `AI_CONVENTIONS.md` §6).
   - `knowledge/guardrails/injection_scan.py`: `find_instructions` → `find_injection_phrases`.
   - Ghi nhận ngoại lệ `console/engines/demo_plate_generator.py` trong ADR-0005 và `AI_CONVENTIONS.md` §2.
5. **Đồng nhất tên file ↔ tên class/singleton trong `app/infra/`:**
   - `monitoring/ai_logger.py`: `AiTelemetryLogger` / `ai_telemetry_logger` → `AiLogger` / `ai_logger`.
   - `datalake/occupancy_reader.py`: `OccupancyHistoryReader` → `OccupancyReader`.
   - `datalake/session_exporter.py`: `ParkingSessionExporter` → `SessionExporter`.
   - `model_registry/artifact_store.py`: `ModelArtifactRegistry` / `get_model_artifact_registry` → `ArtifactStore` / `get_artifact_store`.
   - `storage/object_store.py`: `SignedUrlObjectStore` → `ObjectStore`.
6. **Tách toàn bộ Pydantic schema khỏi `app/api/rest/routes/*_controller.py` sang `app/api/rest/schemas/*_schema.py`:**
   - Tạo 8 file schema (`copilot_schema.py`, `vision_schema.py`, `console_auth_schema.py`, `console_copilot_schema.py`, `console_member_schema.py`, `console_model_schema.py`, `console_tools_schema.py`, `console_vision_schema.py`) theo đúng `AI_CONVENTIONS.md` §3.
7. **Tự động kiểm bằng `script/check_core_layout.py` và dọn sạch cổng kiểm toàn cục (`docs/check_naming.py`):**
   - Thêm `naming_violations()` kiểm `dtos/<tên>_dto.py`, `services/<stem>_service.py`, `class <Stem>Service`, singleton `<stem>_service`, cấm re-export trong `services/__init__.py`, cấm khai báo `@dataclass` trong `services/`, và cấm khai báo class trực tiếp trong `app/api/rest/routes/*_controller.py`.
   - Đổi tên `training/checkmodel.py` → `training/check_model.py`, `clean_history.sh` → `clean-history.sh`, tách mã hồ sơ trùng (`ISSUE-007-copilot-rag-heldout-dataset` → `ISSUE-028`, `ISSUE-020-vision-anpr-pipeline-and-vision-lab-upgrade` → `ISSUE-029`), và thu gọn `README.md` về ≤ 120 dòng theo C1.
