# 📐 ADR-0004: llama-server local chạy một slot, ngữ cảnh 4096, để vừa GPU 4 GB cùng ANPR

> **Đích:** `docs/projects/adrs/10-2026/0004-llama-server-mot-slot-vua-vram-4gb.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Accepted |
| **Ngày** | 2026-10-26 |
| **Người quyết định** | HiTranquility (chọn viết ADR thật cho hồ sơ Final Project, [bug-032](../../bugs/bug-032-ho-so-final-project-lech-voi-repo/bug.md)) |
| **Phạm vi** | IPLMS-AI: `app/infra/llm/llama_server_manager.py`, `app/config/llm_config.py` |

## Bối cảnh

Máy chạy thử của nhóm dùng NVIDIA GTX 1650 (4 096 MiB VRAM), phải chứa cả LLM của Copilot lẫn pipeline ANPR. Cấu hình mặc định của `llama-server` (nhiều slot song song, ngữ cảnh lớn) cấp phát trước KV cache cho mọi slot. Theo ca lỗi 1 trong `AI_USAGE.md`, tổng nhu cầu vượt 4.8 GB, VRAM chạm trần và tính toán bị đẩy sang CPU.

Hồ sơ nộp bài gọi quyết định này là "ADR-0009" mà không có file; ADR-0009 ở repo gốc là chuyện khác.

## Quyết định

Khi `AI_LLM_PROVIDER=local`, `LlamaServerManager` khởi động `llama-server` với tham số lấy từ `LlmConfig`:

| Tham số | Giá trị | Env |
|---|---|---|
| `-np` (số slot KV cache) | 1 | `AI_LOCAL_LLM_PARALLEL_SLOTS` |
| `-c` (độ dài ngữ cảnh) | 4096 | `AI_LOCAL_LLM_CTX_SIZE` |
| `-ngl` (số layer lên GPU) | 33 (toàn bộ Qwen3.5-4B-Q4_K_M) | `AI_LOCAL_LLM_GPU_LAYERS` |
| `--reasoning-budget` | 0 | cố định trong code |

Một slot nghĩa là các yêu cầu Copilot xếp hàng thay vì chạy song song. Ngữ cảnh 4096 token đủ cho prompt hệ thống cộng top-k 5 đoạn quy chế (`rag_top_k`).

Provider mặc định hiện là `ollama` với `qwen2.5:0.5b` (`DEFAULT_LOCAL_LLM_MODEL`), cũng chọn để vừa 4 GB; ADR này áp cho đường `local`.

## Các phương án đã cân nhắc

- **A. Giữ mặc định nhiều slot.** Phục vụ song song tốt hơn nhưng tràn VRAM trên GTX 1650 (ca lỗi 1, `AI_USAGE.md`). Không chọn.
- **B. Offload một phần layer sang CPU.** Vừa VRAM nhưng độ trễ tăng mạnh (CPU 100% theo ca lỗi 1). Không chọn.
- **C. Gọi API LLM đám mây.** Không tốn VRAM, nhưng gửi câu hỏi người dùng ra ngoài và tốn tiền mỗi lượt; vẫn giữ làm provider `openai` tuỳ chọn.

## Hệ quả

### Được

- LLM và ANPR cùng chạy trên một GPU 4 GB.
- Tham số đổi được bằng env cho máy mạnh hơn, không sửa code.

### Đánh đổi

- Hai người hỏi cùng lúc thì một người chờ; không hợp tải đồng thời cao.
- Số đo VRAM và độ trễ ghi trong `AI_GUIDE.md` §6 (≈2.93 GB, ≈2.12 s) là số nhóm tự đo trên máy dev; repo chưa có script đo lặp lại. Đổi model hoặc tham số thì đo lại bằng `nvidia-smi`.

## Bằng chứng và liên kết

- Code: `app/infra/llm/llama_server_manager.py` (lệnh khởi động), `app/config/llm_config.py` (`local_llm_*`).
- Hồ sơ: `AI_USAGE.md` ca lỗi 1 (VRAM OOM).
