# 🤖 AI Usage Log (AI_USAGE.md)
**Project:** IPLMS AI Microservice (Intelligent Parking Lot Management System — AI Core)  
**Course:** New Technologies in Software Engineering · Academic Year 2026–2027  
**Module Owner:** AI & Computer Vision Engineering Team  

---

## 1. Tuyên Bố Liêm Chính Học Thuật (Academic Integrity Declaration)

Theo quy định tại **Mục 5.3 của Đề cương đồ án (Final Project Assignment Guidelines)**:
> *"A file AI_USAGE.md in the repo that lists the main parts generated with AI tools, the tool used, the key prompt, and what you checked or changed in the generated code. Include at least 2 cases where AI-generated code was wrong or not good enough, and how you found and fixed it. Using AI tools without listing them in the log counts as academic misconduct."*

Nhóm phát triển khẳng định:
- Tất cả các công cụ AI được sử dụng trong dự án đều được khai báo minh bạch, đầy đủ trong tài liệu này.
- Mọi đoạn mã do AI tạo ra đều được thành viên phụ trách module **trực tiếp rà soát, kiểm thử đơn vị (Unit Test), đo đạc tài nguyên (VRAM/RAM/CPU), và tái cấu trúc (refactor)** để bảo đảm tính đúng đắn, an toàn và tối ưu trước khi đưa vào codebase chính thức.

---

## 2. Danh Sách Công Cụ AI Được Sử Dụng

1. **Google Antigravity / Gemini 2.5 Flash & Pro (DeepMind Engine):** Hỗ trợ thiết kế kiến trúc microservice, phát triển pipeline RAG local, tối ưu hóa cờ biên dịch Clang của llama-server, gỡ lỗi CUDA VRAM và viết bộ kiểm chuẩn.
2. **Claude 3.7 Sonnet / Cursor:** Hỗ trợ sinh khung mã nguồn FastAPI REST, định nghĩa Pydantic V2 DTOs và sinh gRPC stubs từ file `.proto`.
3. **Claude Code (Claude Opus 5.5, Anthropic):** Viết AI Console nội bộ (IPLMS ISSUE-126: `ai/ui`, `app/console_main.py`, `app/core/console/**`, kênh A2, P6) và tích hợp nhánh — chi tiết ở mục 3b.
4. **Unsloth Qwen3.5 GGUF Tools:** Cung cấp mô hình lượng tử hóa `Qwen3.5-4B-Q4_K_M.gguf` chạy trực tiếp trên GPU.

---

## 3. Nhật Ký Chi Tiết Các Phần Mã Nguồn Được Sinh Bằng AI

| STT | Thành phần / File mã nguồn | Công cụ AI | Câu nhắc chính (Key Prompt) | Phần AI đã sinh ra | Phần người lập trình đã kiểm tra, phát hiện và thay đổi |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **ANPR Vision Pipeline**<br>[`app/core/vision/engines/anpr_engine.py`](app/core/vision/engines/anpr_engine.py) | Antigravity | *"Tối ưu hóa pipeline ANPR chạy trên GPU NVIDIA GTX 1650, kết hợp YOLOv8 detector và EasyOCR recognizer."* | Khung hàm detect box bằng YOLO, cắt crop ảnh và gọi EasyOCR toàn khung hình. | **Đã sửa đổi lớn:** Đảo ngược chu trình (chỉ OCR vùng biển số thay vì full ảnh); thêm padding 6%-8% chống cắt đứt chữ số đầu; bổ sung bộ lọc cú pháp biển số Việt Nam (TT 24/2023) sửa lỗi nhầm `B0F` $\to$ `30F`. |
| **2** | **Vehicle Classifier CNN**<br>[`app/core/vision/engines/vehicle_classifier.py`](app/core/vision/engines/vehicle_classifier.py) | Claude 3.7 | *"Viết class inference cho model PyTorch NetV2 phân loại xe máy, ô tô, xe tải từ ảnh crop."* | Lớp `VehicleClassifier` nạp trọng số `.pth` và thực hiện softmax phân loại 3 nhãn. | **Đã kiểm tra & sửa đổi:** Thêm bộ chuyển đổi `device = 'cuda' if torch.cuda.is_available() else 'cpu'`; thêm cơ chế kiểm tra kích thước ảnh tối thiểu $> 32\times 32$ để tránh văng ngoại lệ `ZeroDivisionError`. |
| **3** | **Local LLM Server Manager**<br>[`app/infra/llm/llama_server_manager.py`](app/infra/llm/llama_server_manager.py) | Antigravity | *"Tạo process manager trong Python để tự động kích hoạt `llama-server.exe` với mô hình Qwen3.5-4B-GGUF trên GPU GTX 1650."* | Khởi chạy `subprocess.Popen` gọi `llama-server.exe` với các tham số mặc định. | **Đã sửa đổi triệt để (Ca lỗi 1):** Khóa cứng tham số `-np 1` (đơn slot KV cache) và `--reasoning-budget 0` để không bị tràn VRAM 4GB; thêm endpoint `/health` polling và đăng ký `atexit.register` để dọn dẹp tiến trình khi tắt app. *Cập nhật 2026-10-27 (A-41, ISSUE-019):* runtime hiện **không** tự bật `llama-server` từ Python — app nối tới `ollama` hoặc `llama-server` chạy ngoài; file này chỉ còn là helper dev, chưa được pipeline gọi. |
| **4** | **Dual Backend LLM Factory**<br>[`app/infra/llm/llm_factory.py`](app/infra/llm/llm_factory.py) | Antigravity | *"Viết LLM adapter hỗ trợ cả OpenAI Responses API và Chat Completions API của local llama.cpp server."* | Class `LlmFactory` khởi tạo `AsyncOpenAI` client trỏ tới URL tương ứng. | **Đã kiểm tra & bổ sung:** Viết hàm `_strip_thinking_tags()` dùng regex loại bỏ triệt để thẻ suy luận `<think>...</think>` của Qwen3.5; bổ sung cơ chế fallback tự động chuyển sang local khi không có API key. |
| **5** | **RAG Retrieval Engine**<br>[`app/core/copilot/engines/rag_pipeline.py`](app/core/copilot/engines/rag_pipeline.py) | Antigravity | *"Xây dựng RAG pipeline tra cứu quy chế bãi xe, có fallback ngoại tuyến từ file JSON seed khi chưa bật pgvector."* | Hàm `_retrieve_from_seed` tìm kiếm từ khóa chuỗi thô trong `regulations_seed.json`. | **Đã sửa đổi sâu (Ca lỗi 2):** Xóa bỏ so khớp chuỗi thô vì dính lỗi hư từ tiếng Việt; viết bộ tách từ ngữ nghĩa, lọc 35 stopwords tiếng Việt và hiệu chuẩn công thức tương đồng cosine để tuân thủ ai ADR-0002. |
| **6** | **LangGraph Dispute Workflow**<br>[`app/core/copilot/engines/dispute_workflow/graph.py`](app/core/copilot/engines/dispute_workflow/graph.py) | Cursor | *"Xây dựng LangGraph StateGraph cho quy trình xử lý khiếu nại bãi xe có node phê duyệt của con người."* | Định nghĩa các nodes: `load_evidence`, `analyze_evidence`, `draft_recommendation`, `finalize`. | **Đã kiểm tra & bổ sung:** Thiết lập nút chặn `interrupt` bắt buộc tại node `request_human_review` theo chuẩn **Mục 4.1.B** (không cho phép AI tự ý thay đổi dữ liệu hoặc giải ngân tiền khi chưa có xác nhận từ Quản lý). |
| **7** | **Multi-Format Ingestion Service**<br>[`app/core/knowledge/services/ingestion_service.py`](app/core/knowledge/services/ingestion_service.py) | Claude 3.7 | *"Viết service bóc tách văn bản từ PDF, DOCX, TXT và Markdown, sau đó chunking thành các đoạn nhỏ."* | Code sử dụng `pypdf` và `docx` để trích xuất text và chia nhỏ theo độ dài ký tự. | **Đã sửa lỗi (Ca lỗi 3):** Bổ sung thuộc tính `duration_ms` cho DTO; thêm cơ chế tự động ghi đồng bộ vào `regulations_seed.json` để tài liệu upload mới có thể tìm kiếm được ngay lập tức ở chế độ local offline. |
| **8** | **Automated Setup Scripts**<br>[`setup-dev.ps1`](setup-dev.ps1) & [`setup-dev.sh`](setup-dev.sh) | Antigravity | *"Tạo script tự động hóa cài đặt môi trường cho lập trình viên mới trên Windows và Linux."* | Cài đặt `.venv`, `requirements.txt` và sinh gRPC stubs. | **Đã mở rộng thành 7 bước:** Bổ sung bước 5 tự động tải `Qwen3.5-4B-Q4_K_M.gguf` (~2.55 GB) từ HuggingFace và tải prebuilt `llama-server` CUDA 12.4 DLLs nếu phát hiện có GPU NVIDIA. |
| **9** | **SSE Streaming Response Pipeline**<br>[`app/api/rest/routes/copilot_controller.py`](app/api/rest/routes/copilot_controller.py)<br>[`app/core/copilot/engines/rag_pipeline.py`](app/core/copilot/engines/rag_pipeline.py) | Antigravity | *"Hiện thực Server-Sent Events (SSE) stream_query cho Copilot với kiểm duyệt Guardrail ai ADR-0002 và truyền phát từng token về UI."* | Khung hàm generator yielding chuỗi thô từ LLM qua `StreamingResponse`. | **Đã tái cấu trúc chặt chẽ:** Tích hợp kiểm duyệt an toàn ngay tại đầu vào (chặn Prompt Injection và Out-of-Scope phát sinh refusal stream có cấu trúc); bổ sung terminal chunk đóng gói đầy đủ `sources`, `confidence`, `prompt_version`, `latency_ms`; bổ sung cơ chế fallback tự động nếu kết nối LLM streaming bị ngắt; hỗ trợ cả `POST` (JSON body) và `GET` (`EventSource` tương thích trình duyệt). |
| **10** | **Admin AI Telemetry & Cost Analytics**<br>[`app/infra/monitoring/ai_logger.py`](app/infra/monitoring/ai_logger.py)<br>`static/index.html` (?? g? ? `747ed19`, dashboard chuy?n v?o AI Console `ui/`) | Antigravity | *"Xây dựng dashboard quản trị theo dõi AI telemetry, token, độ trễ và ước tính chi phí tiết kiệm so với cloud LLM."* | Lớp logging in-memory và giao diện bảng hiển thị request cơ bản. | **Đã nâng cấp toàn diện:** Thêm cơ chế tự động nạp lại lịch sử từ `var/log/ai_requests.jsonl` khi khởi động app để không mất dữ liệu; tính toán tự động chi phí đối ứng GPT-4o; tích hợp 2 biểu đồ trực quan hóa bằng Chart.js (Doughnut trạng thái request & Bar biểu đồ xu hướng độ trễ); bảng Audit Log thời gian thực có gắn nhãn màu phân loại trạng thái (SUCCESS, REFUSED, FALLBACK, ERROR). |


> **Ghi chú tích hợp (2026-10-17, IPLMS ISSUE-126 phase-6 mục 6.4):** khi gộp `khoa-develop` vào nhánh chung, các mục **4, 5, 7** ở trên mô tả code **không** được đưa vào `develop`: `llm_factory.py` và `rag_pipeline.py` giữ bản `develop` (profile model + telemetry ADR-0049, chặn tái nhập bug-011); fallback ghi tài liệu vào `regulations_seed.json` của `ingestion_service.py` bị bỏ vì trả `SUCCESS` khi embedding lỗi và đi vòng cổng xuất bản. Các file đó còn nguyên trên nhánh `khoa-develop`. Mục 3 (`llama_server_manager.py`) có trong `develop` nhưng chưa được pipeline gọi.

### 3b. Claude Code — AI Console nội bộ (IPLMS ISSUE-126)

Toàn bộ code dưới đây do Claude Code viết theo yêu cầu của chủ đồ án; **chủ module (M1–M4 theo §Chia việc của ISSUE-126) cần đọc lại và ghi xác nhận vào cột cuối** trước khi nộp (đề Final §5.3).

| STT | Thành phần / File | Công cụ AI | Yêu cầu chính | Phần AI đã sinh | Đã kiểm / sửa gì (chủ module bổ sung) |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **9** | **Quyền + audit** — `app/core/console/engines/access_policy.py`, `app/infra/database/console_store.py` | Claude Code | *"AI console nội bộ, 7 vai trò, audit chỉ-thêm"* (IPLMS ADR-0048) | 7 vai trò × 15 quyền một nguồn; trigger chặn UPDATE/DELETE/TRUNCATE trên `audit_event` | Test ma trận quyền + test DB thật trên Postgres 16 tạm. **Chủ M1 (HiTranquility / Phát) đã duyệt:** xác nhận logic RBAC 7 vai trò × 15 quyền (`test_console_access.py`), kiểm tra cơ chế trigger cấm sửa/xóa `audit_event` trên Postgres 16. |
| **10** | **Đăng nhập** — `app/infra/identity/*`, `app/core/console/services/auth_service.py` | Claude Code | *"Google OIDC + TOTP bắt buộc, admin khẩn cấp"* | OIDC Authorization Code + PKCE + nonce, TOTP chống dùng lại mã, phiên cookie httpOnly, step-up | Rà lại 2026-10-17: thiếu giới hạn thử sai → sửa (Ca lỗi 4). **Chủ M1 (HiTranquility / Phát) đã duyệt:** xác nhận luồng OIDC PKCE + Fernet mã hoá TOTP secret; đã kiểm thử vá Ca lỗi 4 (giới hạn 5 lần thử sai, hủy phiên `TOO_MANY_ATTEMPTS` và khóa 15 phút). |
| **11** | **Telemetry Copilot** — `app/infra/database/ai_request_log_store.py`, `usage_service.py` | Claude Code | *"Ghi mỗi request AI vào DB, che PII, dashboard mức dùng"* (ADR-0049) | Bảng `ai_request_log`, HMAC user, tóm tắt mức dùng, 👍/👎 | Test unit + DB (`test_copilot_usage.py` 17/17 pass). **Chủ M2 (Dương @23110012) đã duyệt:** xác nhận schema bảng `ai_request_log` và advisory lock, cơ chế băm ẩn danh `user_hash` bằng HMAC-SHA256, bộ lọc `pii_redactor` che PII trên câu hỏi/trả lời trước khi lưu, ghi log bất đồng bộ không làm chậm luồng trả lời (`record_soon`/`drain`), tách biệt lượt thử `console_try` khỏi thống kê sản phẩm (ADR-0050 §3), và luồng đánh giá 👍/👎 trong hạn lưu. |
| **12** | **Giao diện** — `ai/ui/**` | Claude Code | *"React + Vite, Hallmark, 0 CDN"* | Trang đăng nhập/TOTP, Copilot Lab, Vision (gán nhãn, duyệt bốn mắt, golden, model, ngưỡng), Công cụ thử, biểu đồ đường cong ngưỡng | `tsc` + `vite build`; lúc đầu vitest chưa chạy được trên Node 22.14 (Ca lỗi 5), CI đã thêm job. **Kiểm lại 2026-10-27 — Dương (@23110012), người viết test UI ở ISSUE-008/009/010/020, ký thay vì M3 chưa có chủ chính thức (ISSUE-018):** `tsc --noEmit` PASS, `vitest run` **96/96 PASS** (21 file: `client.test.ts` lỗi mạng/phiên hết hạn, `CopilotLabPage.test.tsx`, `CrossRoleDemoLoop.test.tsx` luồng liên vai, `ReviewRowNames.test.tsx` lọc cờ chất lượng, `SettingsPage.test.tsx`). Đã sửa thêm: chip lọc dùng `role="group"` + `aria-pressed`, mã hành động audit gom về `auditActionCodes.json`. |
| **13** | **Kênh A2 + P6** — `backend/src/modules/Vision/workers/console-export.worker.ts`, `DatasetService.ExportForConsole` / `GetAcceptPolicy` | Claude Code | *"Backend xuất một chiều ảnh cắt + nhãn; kéo ngưỡng đã duyệt"* (ADR-0048 §5, ADR-0051) | Worker theo watermark, HMAC group/area; RPC đọc `accept_policy` APPROVED; platform khoá ô ngưỡng khi console quản lý | jest Vision 55/55, test DB AI 19 OK (`test/test_console_vision_import.py`, `test/test_console_vision_lab.py`). **Chưa E2E trên stack dev — bị chặn có hồ sơ:** cần chủ đồ án duyệt chạy migration `1803000000000` và bật `VISION_CONSOLE_EXPORT_*` trên stack dùng chung ([ISSUE-017](docs/projects/issues/10-2026/ISSUE-017-phan-ai-cua-iplms-issue-126/issue.md)). M4 chưa có chủ (ISSUE-018); phần AI phía nhận đã được Dương (@23110012) đọc lại cùng ISSUE-020. Phần code backend cần chủ M4 xác nhận ở repo gốc IPLMS khi được giao. |
| **14** | **Công cụ thử, tri thức & Cài đặt** — `ui/src/pages/Settings/SettingsPage.tsx`, `app/infra/llm/llm_factory.py`, bảng `copilot_eval_candidate`, `app/script/seed_console_demo.py` (ISSUE-007, ISSUE-018, ISSUE-019) | Claude Code / Antigravity | *"Trang Cài đặt phần cứng/policy; lưu ứng viên eval vào DB thay vì file; seed demo"* | Trang Settings, client LLM khởi tạo lười, bảng ứng viên eval, script seed số liệu demo | **Dương (@23110012) kiểm & sửa:** AI khởi tạo `AsyncOpenAI` không khoá → nhiều request đồng thời tạo nhiều client (Ca lỗi 6a) → thêm `asyncio.Lock` (`e7696a2`, `test_llm_factory`); ứng viên eval chuyển từ file JSON sang DB có hạn lưu + che PII (A-37/A-73); seed bỏ số metrics bịa, gắn nhãn `[DEMO]` và không tự promote (A-7/A-70/A-71). |
| **15** | **Hồi quy quyền 7 vai, lỗi mạng/phiên, luồng liên vai** — `test/test_console_access.py`, `ui/src/api/client.test.ts`, `ui/src/pages/Vision/CrossRoleDemoLoop.test.tsx` (ISSUE-008/009/010) | Claude Code / Antigravity | *"Viết test hồi quy ma trận quyền và test UI khi mạng lỗi/phiên hết hạn"* | Khung test ma trận vai × quyền, mock fetch lỗi | **Dương kiểm & sửa:** `test_console_access.py` đối chiếu trực tiếp với `access_policy` (một nguồn quyền) thay vì bảng do AI tự chép; `client.test.ts` kiểm lỗi 401 giữ đúng `status`/`code` (vd `MFA_REQUIRED`) để UI xử lý phiên; test Python + 96 test Vitest PASS. |
| **16** | **Pipeline ANPR & Vision Lab 4 mắt** — `app/core/vision/engines/anpr/preprocess.py`, `anpr/plate_text.py`, `anpr_engine.py`, `ui/src/pages/Vision/ReviewPage.tsx` (ISSUE-020) | Antigravity | *"Đánh giá chất lượng ảnh cắt (mờ/chói/nghiêng/2 dòng), giảm chói trước OCR, sửa nhầm ký tự biển 5 số"* | `assess_crop_quality`, `suppress_glare_for_ocr`, `correct_plate_confusions`, `format_vietnam_plate`, chip lọc cờ chất lượng | **Dương kiểm & sửa (Ca lỗi 6b):** bản AI chạy LUT nén sáng rồi mới CLAHE nên CLAHE kéo vùng chói về 255 lại, và bỏ qua bước enhance khi ảnh hợp lệ nhưng chói → đảo thứ tự (CLAHE trước, LUT sau) và thêm điều kiện `glare` vào `should_enhance`; giữ nguyên biển 4 số khi sửa nhầm chữ số. 87/87 test ANPR PASS (`test_anpr_pipeline_upgrade.py`). |

### Ca lỗi 4 (AI Console): đăng nhập không giới hạn số lần thử sai

- **AI đã sinh:** `ConsoleAuthService._accept_code` trả `TOTP_INVALID` mỗi lần sai, không đếm; `password_login` cũng vậy. Mã TOTP 6 số → có thể dò hết 10⁶ mã từ máy nội bộ.
- **Phát hiện:** rà phần đăng nhập trước khi mở PR tích hợp (đọc code, tìm `attempt/lock/rate` không thấy).
- **Sửa (`ai@3de90e4`):** 5 lần sai TOTP trong một phiên → huỷ phiên (`TOO_MANY_ATTEMPTS`), ghi `audit_event`; 5 lần sai mật khẩu khẩn cấp → khoá 15 phút, thông báo vẫn chung chung. Thêm 2 test service + kiểm SQL trên Postgres thật.

### Ca lỗi 5 (AI Console): CI không chạy giao diện

- **AI đã sinh:** `ai/ui` có `typecheck`/`test`/`build` nhưng workflow `ci.yml` chỉ chạy Python → acceptance "tsc + vite build xanh" không được kiểm tự động.
- **Phát hiện:** chạy lại baseline 2026-10-17, vitest không khởi động được trên Node 22.14 (undici 8 cần zlib zstd) và CI cũng không có job nào bắt được.
- **Sửa (`ai@3de90e4`):** thêm job "Build AI Console UI" (Node 22, `pnpm install --frozen-lockfile`, typecheck, vitest, build).

---

## 4. Phân Tích 2 Trường Hợp AI Sinh Mã Lỗi Điển Hình & Cách Khắc Phục (Required by Section 5.3)

### 🔴 Ca Lỗi 1: Tràn Bộ Nhớ VRAM (OOM) & Độ Trễ Bùng Nổ Do Cấu Hình Mặc Định Của `llama-server`

#### 1. Mô tả đoạn mã do AI tạo ra:
Khi được yêu cầu viết lệnh khởi chạy `llama-server` cho mô hình `Qwen3.5-4B-GGUF`, AI đề xuất đoạn mã đơn giản:
```python
# Đoạn mã ban đầu do AI sinh ra trong llama_server_manager.py (helper dev; runtime hiện không tự gọi — A-41)
cmd = [
    "llama-server.exe",
    "-m", "model/checkpoint/llm/Qwen3.5-4B-Q4_K_M.gguf",
    "--port", "8005",
    "-ngl", "33",
]
```

#### 2. Vì sao đoạn mã này SAI và NGUY HIỂM:
- Card đồ họa triển khai thực tế là **NVIDIA GeForce GTX 1650 chỉ có đúng 4.096 MiB VRAM**.
- `llama-server` theo mặc định tự động khởi tạo **4 slots phục vụ song song (`-np 4`)** với context size **8192 tokens**.
- Với 4 slots $\times$ 8192 tokens, bộ nhớ đệm KV cache đòi cấp phát trước lên đến **2.2 GB VRAM**. Khi cộng thêm **2.55 GB** trọng số mô hình và **120 MB** CUDA runtime, tổng nhu cầu bộ nhớ vượt quá **4.8 GB**.
- **Hậu quả thực tế:**
  1. `llama-server` cảnh báo `abort fit params`, không thể offload hết vào GPU mà bị ép đẩy các tầng Transformer sang CPU.
  2. Thời gian phản hồi cho mỗi câu hỏi tăng vọt từ 2 giây lên **45.2 giây** (chậm gấp 20 lần).
  3. Khi gọi đồng thời với pipeline Vision (YOLOv8 + EasyOCR), hệ thống lập tức bị sập với lỗi `CUDA out of memory`.
  4. Hơn nữa, Qwen3.5 tự động bật chế độ suy luận `<think>...</think>`, tự lẩm bẩm sinh hàng trăm token vô ích trước khi trả lời.

#### 3. Cách nhóm phát hiện lỗi:
Thành viên nhóm chạy lệnh kiểm tra tiến trình `nvidia-smi` và soi log khởi động của `llama-server` tại `var/log/`. Phát hiện VRAM bị đẩy kịch trần 4096 MiB và CPU load nhảy lên 100%.

#### 4. Giải pháp khắc phục của nhóm:
Nhóm đã tái cấu trúc lại toàn bộ tham số khởi chạy trong [`app/infra/llm/llama_server_manager.py`](app/infra/llm/llama_server_manager.py) (các tham số này cũng là cấu hình khuyến nghị khi chạy `llama-server` ngoài process, vì runtime hiện không tự spawn server — A-41):
1. Đặt cứng `-np 1`: Vì FastAPI microservice phục vụ tuần tự theo event-loop, chỉ cần cấp phát 1 inference slot duy nhất, cắt giảm KV cache từ 2.2 GB xuống còn **270 MiB**.
2. Giới hạn `-c 4096`: Vừa đủ cho tài liệu quy chế bãi xe mà không lãng phí VRAM.
3. Thiết lập `--reasoning-budget 0`: Triệt tiêu hoàn toàn vòng lặp suy luận `<think>`, buộc mô hình đi thẳng vào câu trả lời quy chế.
4. **Kết quả sau khi sửa:** Toàn bộ 33/33 layers được nạp trọn vẹn 100% vào GPU. Tổng VRAM chiếm dụng chỉ còn **2.93 GB / 4.09 GB (71.7%)**, chừa lại **> 1.15 GB VRAM** cho ANPR, tốc độ sinh đạt **~20.7 tokens/giây** và độ trễ giảm ngoạn mục xuống còn **2.12 giây**!

---

### 🔴 Ca Lỗi 2: Trùng Lặp Hư Từ Tiếng Việt Gây Bịa Đặt Thông Tin (Stopword Collision Hallucination)

#### 1. Mô tả đoạn mã do AI tạo ra:
Khi xây dựng hàm tra cứu tài liệu ngoại tuyến `_retrieve_from_seed`, AI viết một đoạn so khớp chuỗi con sơ sài:
```python
# Đoạn mã ban đầu do AI sinh ra trong rag_pipeline.py
def _retrieve_from_seed(self, query: str) -> list[dict]:
    keywords = query.lower().split()
    scored = []
    for item in seeds:
        score = sum(1 for kw in keywords if kw in item["content"].lower())
        if score > 0:
            scored.append({"item": item, "score": score})
    return scored
```

#### 2. Vì sao đoạn mã này SAI và VI PHẠM ai ADR-0002:
- Trong tiếng Việt, các từ như *"gia"*, *"có"*, *"cho"*, *"và"*, *"là"* xuất hiện với tần suất cực cao trong các văn bản quy chế (ví dụ: *"tham gia giao thông"*, *"có trách nhiệm"*).
- Khi người dùng gửi một câu hỏi hoàn toàn ngoài luồng:
  > *"Cách nấu phở bò gia truyền Hà Nội"*
- Từ *"gia"* trong *"gia truyền"* bị khớp nhầm vào từ *"tham gia"* trong Quy chế bãi xe!
- Kết quả là `score = 1 > 0`. Thuật toán xem đây là tài liệu liên quan, nạp điều khoản đỗ xe vào context và gửi cho LLM.
- **Hậu quả nghiêm trọng:** LLM nhận được ngữ cảnh bãi xe nhưng lại cố gắng "chiều lòng" người dùng bằng cách bịa ra: *"Bãi xe IPLMS có quy định về việc mang phở bò gia truyền vào khu vực đỗ xe..."*. Điều này vi phạm trực tiếp nguyên tắc tối thượng của hệ thống: **ai ADR-0002 ("Thà lỗi hơn bịa — Strict Abstention")**.

#### 3. Cách nhóm phát hiện lỗi:
Nhóm thiết kế bộ kiểm chuẩn nghiêm ngặt kiểm chuẩn ngoài miền (bản gốc `test_rag_rigorous_eval.py` không có trong lịch sử Git của repo này; kịch bản tương đương nay nằm ở [`test/test_copilot_streaming_api.py`](test/test_copilot_streaming_api.py) với câu hỏi *"Cách nấu phở bò gia truyền Hà Nội"*). Khi chạy kịch bản số 6 (`test_negative_query_out_of_domain_strict_rejection`), bài kiểm tra bị **FAIL** vì số lượng chunk trả về khác 0 và câu trả lời không phải là thông báo từ chối.

#### 4. Giải pháp khắc phục của nhóm:
Nhóm đã thay thế toàn bộ thuật toán khớp chuỗi bằng một bộ xử lý ngôn ngữ tự nhiên tiếng Việt chặt chẽ tại [`app/core/copilot/engines/rag_pipeline.py`](app/core/copilot/engines/rag_pipeline.py):
1. **Lập danh sách 35 Hư từ tiếng Việt (Vietnamese Stopwords):** Loại bỏ hoàn toàn các từ không mang nghĩa thực tế như `"là", "có", "và", "của", "cho", "các", "tại", "trong", "gia", "này", "thì", "khi", "những"`.
2. **So khớp ranh giới từ nguyên bản (Regex Word Boundaries):** Dùng `\b` và `re.findall(r'\w+', q_lower)` để chỉ khớp từ độc lập chứ không khớp chuỗi con ngẫu nhiên.
3. **Hiệu chuẩn công thức điểm tương đồng (Similarity Formula Calibration):**
   $$\text{similarity} = \text{match\_ratio} \times 0.70 + \min\left(1.0, \frac{\text{score}}{\text{len}(\text{keywords}) \times 2.5}\right) \times 0.30$$
4. **Ngưỡng chặn dứt khoát:** Nếu không có chunk nào đạt $\text{similarity} \ge 0.35$, hệ thống lập tức gán `confidence = 0.0`, trả về 0 chunks và kích hoạt kịch bản từ chối lịch sự.
5. **Kết quả sau khi sửa:** Kịch bản hỏi *"Cách nấu phở bò gia truyền"* nhận về **0 chunk**, độ tin cậy **0%**, và hệ thống từ chối dứt khoát không ảo giác. Tất cả 9/9 bài kiểm tra RAG đều đạt PASS 100%!

---

### 🟡 Ca Lỗi 3 (Bổ sung): Sai Lệch Tên Thuộc Tính Giữa DTO và Controller Gây Sập API Upload (500 Error)

#### 1. Mô tả đoạn mã do AI tạo ra:
Trong API Controller `app/api/rest/routes/knowledge_controller.py` (?? g?p v?o [`console_tools_controller.py`](app/api/rest/routes/console_tools_controller.py) ? `747ed19`), AI viết code trả về kết quả nạp tài liệu:
```python
# Controller gọi thuộc tính duration_ms
return {
    "document_id": result.document_id,
    "chunk_count": result.chunk_count,
    "duration_ms": result.duration_ms,  # <-- AI tự bịa ra thuộc tính này
}
```
Tuy nhiên, trong định nghĩa DTO gốc [`app/core/knowledge/dtos/knowledge_dto.py`](app/core/knowledge/dtos/knowledge_dto.py), AI trước đó lại định nghĩa:
```python
class IngestResult(BaseModel):
    document_id: str
    chunk_count: int
    duration_sec: float  # <-- Thuộc tính thực tế là duration_sec!
```

#### 2. Vì sao sai:
Gây ra lỗi sập runtime nghiêm trọng: `AttributeError: 'IngestResult' object has no attribute 'duration_ms'`. Khách hàng tải file PDF/DOCX lên Dashboard Web UI nhận ngay mã lỗi HTTP 500.

#### 3. Cách phát hiện & Khắc phục:
Khi thực hiện kiểm thử tải file PDF mẫu trong Web UI, giao diện báo đỏ. Nhóm kiểm tra log FastAPI, phát hiện ngay vị trí sai lệch kiểu dữ liệu. Nhóm đã bổ sung một `@property` vào `IngestResult`:
```python
@property
def duration_ms(self) -> float:
    """Tự động chuyển đổi giây sang mili-giây để tương thích API."""
    return round(self.duration_sec * 1000.0, 2)
```
Sau khi sửa, tính năng nạp tài liệu hoạt động mượt mà, hỗ trợ cả 2 định dạng thời gian mà không làm vỡ giao diện.

---

### 🟠 Ca Lỗi 4: Thiếu Giới Hạn Thử Sai Mã TOTP (Brute-Force Vulnerability)

#### 1. Mô tả đoạn mã do AI tạo ra:
Khi tạo khung xác thực TOTP trong `ConsoleAuthService.finish_totp`, AI chỉ đơn thuần kiểm tra tính hợp lệ của mã 6 chữ số:
```python
# Đoạn mã ban đầu do AI sinh ra
if not totp.verify(totp_code):
    raise ConsoleAccessDenied("Mã xác thực không đúng")
```

#### 2. Vì sao sai và nguy hiểm:
Mã TOTP chuẩn RFC 6238 gồm 6 chữ số chỉ có 1.000.000 hoán vị với cửa sổ hiệu lực 30–60 giây. Việc không giới hạn số lần thử cho phép kẻ tấn công thực hiện vét cạn (brute-force) qua loop script tự động trong thời gian hiệu lực của mã, vi phạm nghiêm trọng tiêu chuẩn bảo mật hệ thống nội bộ.

#### 3. Cách phát hiện & Khắc phục:
Chủ M1 (HiTranquility / Phát) rà soát mã nguồn theo checklist OWASP Authentication:
1. Thêm cột `totp_attempts` và `locked_until` vào phiên tạm `console_auth_flow`.
2. Giới hạn tối đa **5 lần thử sai**. Nếu vượt quá 5 lần:
   - Ngay lập tức vô hiệu hóa flow xác thực (`status = 'TOO_MANY_ATTEMPTS'`).
   - Khóa IP / tài khoản trong 15 phút.
   - Ghi nhận sự kiện kiểm toán bảo mật `MFA_BRUTE_FORCE_BLOCKED` vào `audit_event`.

---

### 🔵 Ca Lỗi 5: Lệch Xung Nhịp Đồng Hồ (Clock Skew) & Sai Lệch Host Header Trong Google OIDC

#### 1. Mô tả sự cố:
Khi tích hợp đăng nhập Google OIDC qua `google-auth` trên môi trường thực tế tại Windows:
```python
# Đoạn mã ban đầu
id_info = id_token.verify_oauth2_token(
    credential,
    requests.Request(),
    audience=self._client_id,
)
```
Trình duyệt hoàn tất chọn tài khoản Google nhưng khi redirect về endpoint `/console/auth/google/finish`, hệ thống báo lỗi:
> *"Đăng nhập Google không hoàn tất (phiên quá 10 phút hoặc không khớp)."*

#### 2. Vì sao sai:
Nhóm tiến hành phân tích log Uvicorn và phát hiện 2 nguyên nhân gốc rễ:
1. **Clock Skew (Lệch xung nhịp máy trạm):** Đồng hồ hệ điều hành Windows trên máy phát triển bị lệch ~6 giây so với NTP server của Google. Hàm `verify_oauth2_token` mặc định thiết lập sai số bằng 0 (`clock_skew_in_seconds=0`), khiến token vừa cấp từ Google bị đánh giá là `Token used too early` hoặc `expired`.
2. **Host Header Mismatch (`127.0.0.1` vs `localhost`):** Flow cookie `console_auth_flow` được ghi khi truy cập qua `http://localhost:8090`, nhưng callback từ Google Cloud Console lại chuyển hướng về `http://127.0.0.1:8090`. Do khác biệt về tên miền theo chính sách SameSite / Cookie Domain của trình duyệt, cookie xác thực không được đính kèm vào request finish, làm hỏng việc kiểm tra cryptographic nonce.

#### 3. Cách khắc phục:
1. Tại [`app/infra/identity/google_oidc.py`](app/infra/identity/google_oidc.py): Bổ sung tham số dung sai thời gian `clock_skew_in_seconds=120` (cho phép lệch tối đa 2 phút) khi xác thực Google ID token:
   ```python
   id_info = id_token.verify_oauth2_token(
       token_str,
       req,
       self.client_id,
       clock_skew_in_seconds=120,
   )
   ```
2. Tại [`app/api/rest/routes/console_auth_controller.py`](app/api/rest/routes/console_auth_controller.py):
   - Chuẩn hóa tự động giữa `127.0.0.1` và `localhost` để đồng bộ URL redirect và cookie domain.
   - Ghim rõ đường dẫn cookie `path="/console"`, bảo đảm trình duyệt luôn gửi kèm cookie state/nonce.
3. **Kết quả:** Quá trình đăng nhập Google OIDC hoàn thành 100% chỉ trong 1 lần click, tự động cấp quyền Super Admin cho Project Lead (`thebeyondtranquility@gmail.com`).

---

### 🟣 Ca Lỗi 6: Race condition khi khởi tạo LLM client & giảm chói sai thứ tự trong ANPR (Dương @23110012)

#### 6a. `AsyncOpenAI` client khởi tạo không khoá — [`app/infra/llm/llm_factory.py`](app/infra/llm/llm_factory.py)
- **AI đã sinh:** khởi tạo lười kiểu `if self._client is None: self._client = AsyncOpenAI(...)` trong hàm `async`.
- **Vì sao sai:** nhiều request Copilot đến cùng lúc khi app vừa khởi động đều thấy `None` và cùng tạo client → rò kết nối HTTP, cấu hình đổi giữa chừng (Settings) có thể bị ghi đè bởi client cũ.
- **Phát hiện:** cross-review audit-6/7/8 của ISSUE-019, đọc code đường khởi tạo.
- **Sửa (`e7696a2`):** thêm `self._client_lock = asyncio.Lock()` và `async with self._client_lock:` quanh đoạn tạo client; kiểm bằng `python -m unittest test.test_llm_factory`.

#### 6b. Giảm chói biển số làm ngược thứ tự — [`app/core/vision/engines/anpr/preprocess.py`](app/core/vision/engines/anpr/preprocess.py)
- **AI đã sinh:** `suppress_glare_for_ocr` áp LUT nén vùng sáng rồi mới chạy CLAHE; `anpr_engine.py` bỏ qua bước enhance khi ảnh cắt đã khớp định dạng dù có cờ `glare`.
- **Vì sao sai:** CLAHE cân bằng lại histogram nên kéo vùng chói vừa nén về 255 — giảm chói không có tác dụng; ảnh chói nhưng "trông hợp lệ" không được xử lý, OCR dễ đọc nhầm ký tự.
- **Phát hiện:** test `SuppressGlareForOcrTest` và `RunAnprQualityFlagsIntegrationTest` (ISSUE-020) FAIL.
- **Sửa (`36b8b15`, PR #86):** CLAHE trên kênh L (LAB) trước, LUT nén sáng sau, không sửa trực tiếp `crop` gốc; thêm điều kiện `"glare" in crop_quality_flags and not strong_format` vào `should_enhance`. Kết quả 87/87 test ANPR PASS.

---

## 5. Tổng Kết Đánh Giá Cá Nhân Về Việc Ứng Dụng AI

1. **Hiệu quả tích cực:** Công cụ AI giúp đẩy nhanh tốc độ viết mã các đoạn lặp lại (boilerplate, DTOs, regex, bash script), hỗ trợ tra cứu nhanh các cờ tối ưu hóa chuyên sâu của thư viện C++ `llama.cpp`.
2. **Cảnh báo quan trọng:** AI thường xuyên đưa ra các giả định sai lầm về tài nguyên phần cứng (ví dụ: mặc định cấu hình ngốn nhiều VRAM của server lớn, không phù hợp cho card phổ thông 4GB) và dễ tạo ra lỗi logic tinh vi trong ngôn ngữ tiếng Việt (như lỗi trùng hư từ).
3. **Kết luận:** **Không bao giờ tin tưởng mù quáng mã nguồn AI sinh ra.** Mọi dòng mã đều bắt buộc phải đi kèm với bộ kiểm thử tự động (Unit Test / Integration Test / Benchmark Eval) và được con người trực tiếp nghiệm thu trên phần cứng thực tế.
