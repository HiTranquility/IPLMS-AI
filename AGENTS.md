# IPLMS-AI — chỉ dẫn cho coding agents

`IPLMS-AI` là submodule của repo gốc IPLMS (thư mục `ai/`). Mở từ repo gốc thì dùng bộ skill `iplms-*` và `CLAUDE.md` ở gốc; file này đủ để làm việc khi chỉ clone riêng repo này.

## Stack và quy ước

- Python: FastAPI + gRPC cho ANPR, Forecast, Copilot/RAG; huấn luyện ở `training/`, notebook ở `notebook/`.
- Quy ước: [AI_CONVENTIONS](docs/AI_CONVENTIONS.md). Hợp đồng ANPR lấy từ tài liệu này, proto và code; skill `anpr-pipeline` ở repo gốc là bản cũ viết cho C#.
- Mở 1–2 file cùng loại trong cùng thư mục và theo đúng cách đang làm trước khi viết mới.
- Tính năng gọi LLM theo [ADR-0029](../docs/projects/adrs/10-2026/0029-nguyen-tac-guardrail-llm.md) ở repo gốc: LLM không cầm quyền, đầu vào độc mặc định, đầu ra qua kiểm tất định (`app/core/copilot/engines/output_guard.py`), đổi prompt/guard phải chạy lại bộ tấn công.

## Kiểm chứng

- Test dùng `unittest`: `python -m unittest test.<tên_module>` cho file bị ảnh hưởng.
- Đổi field gRPC: chạy `proto/check-proto-sync.py` ở repo gốc và kiểm caller NestJS.
- Không tải/ghi đè checkpoint hay dữ liệu trong `model/`, `data/` khi chưa được giao.
- Build pass không thay cho kiểm hành vi. Báo rõ phần đã chạy, bị chặn và chưa chạy.

## Tài liệu

Hồ sơ riêng của repo ở `docs/`: mọi hồ sơ nằm dưới `projects/` — `suggestions/` (SUGGESTION-NNN), `usecases/` (UC: đặc tả cho dev, bảng + sequence), `adrs/`, `issues/`, `bugs/`, `qas/` — theo [bộ mẫu tối thiểu](docs/templates/README.md). Việc xuyên repo (IDEA/PROB/ADR hệ thống, REQ) ghi ở `docs/` của repo gốc IPLMS và link hai chiều; không đổi SUGGESTION ở đây thành IDEA.

## Git và an toàn

- Chỉ stage đúng file mình sửa; [NEVER] `git add .` / `git add -A`. Message mô tả thay đổi thật và ghi phần chưa làm/chưa test.
- Commit trong repo này trước; cập nhật gitlink ở repo gốc là bước riêng khi thuộc phạm vi.
- Hỏi người dùng trước khi cài package mới, chạy lệnh ghi dữ liệu dùng chung hoặc deploy.
