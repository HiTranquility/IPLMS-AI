# 🏷️ ISSUE-007: Củng cố kết nối DB, quản lý tài liệu tri thức, batch upload và tối ưu phân bổ VRAM 4GB cho Console Tools

> **Đích:** `docs/projects/issues/10-2026/ISSUE-007-console-tools-and-knowledge-management/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ DONE |
| **Ngày tạo** | 2026-10-25 |
| **Ngày hoàn thành** | 2026-11-03 |
| **Ngày đóng** | 2026-11-03 |
| **Người phụ trách** | Khoa (cùng Antigravity) |
| **Phạm vi** | `ai` (backend FastAPI + gRPC stubs + console stores + UI) |
| **Nhánh** | `feature/ISSUE-007-2026-10-console-tools-and-knowledge-management` |

## Mục tiêu

1. **Củng cố kết nối Database:** Tự động fallback linh hoạt giữa các container hostnames (`ai-db`, `database-vector`, `postgres`, `ai_db`) và port mapping của dev (`5435`, `5432`, `AI_DB_HOST_PORT`) để tránh lỗi HTTP 422/500 trên Copilot Overview và Copilot Lab.
2. **Minh bạch kiến trúc phần cứng:** Sửa tên model hiển thị chính xác thành `Qwen3.5-4B-Q4_K_M` (thay vì nhãn `qwen2.5:3b`); bổ sung card chẩn đoán giải thích rõ kiến trúc VRAM an toàn 4GB (Local LLM chạy trên GPU CUDA ~2.93GB; Vision phân bổ CPU để chống OOM).
3. **Quản lý tài liệu tri thức (pgvector):** Hiển thị danh sách các tài liệu đã nạp, hỗ trợ lọc theo danh mục, xem số lượng chunk, phiên bản, trạng thái và xóa tài liệu an toàn (kèm endpoint DELETE và audit log `knowledge.delete`).
4. **Hiện đại hóa nạp tri thức & Batch Upload:** Thay thế input file cũ bằng modern drag-and-drop dropzone; hỗ trợ nạp hàng loạt (multi-file batch queue); tự động reset trạng thái lỗi cũ khi chọn/đổi file.
5. **Cơ chế Fallback Embedding Offline:** Bổ sung deterministic fallback embedder (768 chiều) khi mất kết nối mạng hoặc không có Ollama/OpenAI để đảm bảo nạp dữ liệu offline thành công 100%.

## Tiêu chí chấp nhận

- [x] Endpoint `/tools/system` trả về `llm_model: "Qwen3.5-4B-Q4_K_M"` và `vision_device: "cpu"`.
- [x] Endpoint `DELETE /tools/knowledge/documents/{document_id}` xóa tài liệu, xóa chunk tương ứng trong pgvector và ghi audit log.
- [x] Giao diện Drag & Drop Dropzone hỗ trợ kéo thả nhiều file, file preview chip, chọn danh mục nghiệp vụ.
- [x] Tự động reset lỗi cũ khi chọn tệp, xóa tệp hoặc tạo mã mới.
- [x] Không còn bị chặn bởi lỗi `httpcore.ConnectError` khi máy dev offline.
- [x] Toàn bộ test pass: Unittest backend (38/38) và Vitest frontend (74/74 bao gồm `noHardcodedVi.test.ts`).

## Definition of Done

- [x] Toàn bộ unit test và kiểm thử tích hợp của hạng mục đạt PASS.

