# 🏷️ ISSUE-031: Cô lập test ANPR khỏi `best.onnx` cục bộ và chuẩn hoá type hint tầng `config`/`core`/`mappers`

> **Đích:** `docs/projects/issues/11-2026/ISSUE-031-anpr-test-isolation-and-type-hints/issue.md` — ngoài cùng chỉ file này; `review/review-1.md` ghi kết quả kiểm chứng · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Done |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-11-26 |
| **Ưu tiên** | 🟡 |
| **Ngày tạo** | 2026-11-26 |
| **Ngày đóng** | 2026-11-26 |
| **Người phụ trách** | @HiTranquility |
| **Phạm vi** | IPLMS-AI (`test/test_anpr_pipeline*.py`, `test/test_two_line_plate_parser.py`, `app/config/`, `app/core/`, `app/grpc_server.py`, `app/console_main.py`, `app/api/grpc/mappers/`, `app/api/grpc/interceptors/`, `docs/**`) |

## Mục tiêu

1. Khắc phục 3 unit test ANPR thất bại trên máy có sẵn `data/models/best.onnx` (được ghi nhận ngoài phạm vi ở [ISSUE-030](../ISSUE-030-ai-naming-and-conventions/issue.md)) bằng cách cô lập `VisionConfig.onnx_enabled = False` trong các test mock PyTorch `_state`.
2. Xử lý phần lõi của backlog `B8` từ [AUDIT-009](../../../audits/11-2026/AUDIT-009-naming-va-conventions-ai.md): đạt `0` hàm thiếu type hint ở `app/config/`, `app/core/`, `app/grpc_server.py`, `app/console_main.py`, `app/api/grpc/mappers/` và `logging_interceptor.py` (không chạm `app/api/rest/console_access.py` và `app/main.py` để tránh xung đột với `ISSUE-145`).

## Tiêu chí chấp nhận

- [x] `.\.venv\Scripts\python.exe -m unittest discover -s test -t .` chạy **0 failures** trên máy có `data/models/best.onnx` (`Ran 733 tests in 183.720s — OK (skipped=41)`); có test bảo vệ hồi quy khi ONNX session đã cache nhưng `onnx_enabled=False`.
- [x] `ai_hints.py` đạt `0` thiếu hint tại `app/config/`, `app/core/`, `app/grpc_server.py`, `app/console_main.py`, `app/api/grpc/mappers/` và `logging_interceptor.py` (giảm tổng từ `322/1119` xuống `213/1119`).
- [x] `check_core_layout.py`, `test_check_core_layout.py`, `compileall`, `check_naming.py`, `check_branch_policy.py` và CI trên PR đều pass.

## Kế hoạch

1. Cô lập `VisionConfig.onnx_enabled = False` trong `test/test_anpr_pipeline.py`, `test/test_anpr_pipeline_upgrade.py`, `test/test_two_line_plate_parser.py` và thêm ca bảo vệ → kiểm: `unittest discover`.
2. Bổ sung type hint đầy đủ cho `app/config/` (`5`), `app/core/` (`49`), `app/grpc_server.py` (`1`), `app/console_main.py` (`5`), `app/api/grpc/mappers/` (`41`) và `logging_interceptor.py` (`8`) → kiểm: `ai_hints.py`, `check_core_layout.py`, `compileall`.
3. Lập `review/review-1.md`, cập nhật `AUDIT-009` mục `B8`, mở PR vào `develop`, đợi CI pass, merge và xoá nhánh.

## Hồ sơ liên quan

- [review-1.md](review/review-1.md)
- [ISSUE-030](../ISSUE-030-ai-naming-and-conventions/issue.md)
- [AUDIT-009](../../../audits/11-2026/AUDIT-009-naming-va-conventions-ai.md)
- [AI_CONVENTIONS](../../../../standards/AI_CONVENTIONS.md)
