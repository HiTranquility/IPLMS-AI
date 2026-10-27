# 📐 ADR-0005: Khuôn domain trong `app/core/`: ba thư mục lõi, slot tuỳ chọn có tên cố định, text LLM ra `data/prompts/`

> **Đích:** `docs/projects/adrs/10-2026/0005-khuon-domain-core-ba-thu-muc-va-slot-tuy-chon.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Accepted |
| **Ngày** | 2026-10-27 |
| **Người quyết định** | HiTranquility (chốt trong chat 2026-10-27: chia theo loại → khuôn B → đặt tên domain theo A) |
| **Phạm vi** | IPLMS-AI: `app/core/**`, `data/prompts/`, `app/infra/llm/`, `app/infra/datalake/`; thay [AI_CONVENTIONS §2](../../../standards/AI_CONVENTIONS.md#2-khuôn-một-domain-trong-core) |

## Bối cảnh

AI_CONVENTIONS §2 cũ chỉ cho mỗi domain "đúng ba thư mục" `dtos/ engines/ services/`. Thứ không vừa ba ô đó thì mỗi domain tự đặt chỗ, quét ngày 2026-10-27 thấy:

| Domain | Lệch |
|---|---|
| `copilot` | Thêm `guardrails/`, `prompts/` ngoài khuôn; code an toàn chia hai nơi (`guardrails/guardrail_manager.py` và `engines/output_guard.py`, `engines/pii_redactor.py`); `engines/dispute_workflow/` là đồ thị nhiều bước chứ không phải thuật toán |
| `vision` | `engines/anpr/` là package con nhưng `anpr_engine.py`, `anpr_onnx_engine.py`, `two_line_plate_parser.py` nằm ngoài; ngưỡng tinh chỉnh rải ở `preprocess.py:11-31`, `scoring.py:16`, `plate_text.py:7`, còn luật biển số (`PLATE_*`) ở `core/constants.py` dù chỉ vision dùng |
| `forecast` | `engines/` rỗng; thêm `readers/parquet_lake_reader.py` (689 dòng đọc Parquet), việc của `infra/datalake/` |
| `knowledge_eval`, `console` | Thiếu `dtos/` |

Text gửi LLM cũng phân tán: prompt Copilot nằm ở file có version + hash (`data/prompts/copilot_rag_system_v2.txt`), còn `JUDGE_INSTRUCTIONS` (`knowledge_eval/engines/judge.py:8`) và `GENERATOR_INSTRUCTIONS` (`case_generator.py:11`) viết cứng. Có bốn cặp trùng hoặc lệch nhau:

- `DEFAULT_FALLBACK_PROMPT` (`copilot/prompts/prompt_manager.py:12`) thiếu dòng chống injection mà v2 có.
- Khuôn "CÂU HỎI CỦA NGƯỜI DÙNG… NGỮ CẢNH ĐÃ TRUY XUẤT…" chép 3 lần trong `infra/llm/llm_factory.py` (:202, :262, :435).
- `NO_CONTEXT_ANSWER` (`rag_pipeline.py:27`) trùng từng chữ `DEFAULT_NO_CONTEXT_ANSWER` (`guardrail_manager.py:50`).
- Marker nhận diện câu từ chối có hai bản (`knowledge_eval/engines/grader.py:19`, `app/script/eval_copilot_e2e.py:43`), cả hai dính ngầm vào câu trả lời mẫu.

## Quyết định

1. **Domain = bounded context, trùng tên gRPC service** (`vision`, `copilot`, `knowledge`, `knowledge_eval`, `forecast`, `dataset`, `model_policy`; `console` là domain chỉ có REST). Năng lực bên trong (`anpr`, `rag`, `dispute`) là **package con trong domain**, không phải domain riêng.
2. **Khuôn một domain:**

   ```text
   app/core/<domain>/
   ├── __init__.py     public API (api/ và domain khác chỉ import từ đây)
   ├── dtos/           [bắt buộc] kiểu vào/ra
   ├── engines/        [bắt buộc] thuật toán / model thuần; ≥3 file cùng một năng lực → engines/<năng-lực>/ có façade
   ├── services/       [bắt buộc] điều phối một lượt use case
   ├── workflows/      [tuỳ chọn] đồ thị nhiều bước có checkpoint (LangGraph)
   ├── guardrails/     [tuỳ chọn] luật / regex an toàn cho đầu vào–đầu ra
   ├── constants.py    [tuỳ chọn] hằng số chỉ domain này dùng
   ├── messages.py     [tuỳ chọn] text hiện cho người dùng
   └── README.md       [tuỳ chọn] sơ đồ và mô tả domain
   ```

   Thư mục/file ngoài danh sách thì không được tạo. Cần thêm slot thì sửa ADR này.
3. **Không thuộc `core/`:**
   - Text gửi LLM (system prompt, khuôn user message, JSON schema output) → `data/prompts/<tên>/vN.md` (+ `user.md`, `schema.json` khi có); loader chuyển từ `core/copilot/prompts/` sang `infra/llm/prompts.py`; bản `vN.md` số lớn nhất được dùng. Telemetry giữ dạng nhãn `<tên>_<version>#<hash8>` để backend đọc `promptVersion` không đổi.
   - Đọc file / DB / lake → `infra/`. Ngoại lệ tạm: `forecast/engines/parquet_lake_reader.py` trộn I/O Parquet với baseline giờ và map DTO forecast. Chuyển nguyên file thì `infra/` phải import `core.forecast.dtos`, ngược §1. Tách I/O sang `infra/datalake/` là việc tiếp theo, ghi ở ISSUE-023.
   - Dữ liệu mẫu, adapter giả → `test/` hoặc `app/script/`. Ngoại lệ: `copilot/workflows/dispute/fixtures.py` là adapter hợp đồng mà endpoint mô phỏng dùng khi chạy thật, vì workflow chưa nối backend (`arbitrate_dispute` vẫn trả `FeatureNotImplementedError`). Nối adapter thật thì chuyển file này đi.
4. **Dùng chung:** hằng số dùng ≥2 domain giữ ở gốc `core/constants.py`; hằng chỉ một domain dùng chuyển về `<domain>/constants.py`. Ngưỡng riêng của một module (ví dụ `anpr/preprocess.py`) giữ cạnh code dùng nó. Code dùng chung giữa domain thì **ở lại domain sở hữu** và domain khác import qua `__init__` của nó (ví dụ `app.core.knowledge.find_instructions` cho `copilot` dùng), không tạo thư mục chung mới.
   - **Marker nhận diện câu từ chối ở nơi dùng (`knowledge_eval/engines/grader.py`), không ở `copilot/messages.py`.** Lý do: import `app.core.copilot.messages` sẽ chạy `copilot/__init__.py`, kéo theo service, openai, psycopg2, langgraph (~2,3 s), trong khi `grader.py` cố ý chỉ dùng stdlib. Thay vào đó, `test/test_knowledge_eval.py` trói hai bên: đổi `NO_CONTEXT_ANSWER` mà quên marker thì test đỏ.
5. **Không có fallback prompt viết cứng.** Thiếu file prompt khi khởi động thì báo lỗi ngay; image phải mang `data/prompts/` (bug-042 lo phần đóng gói).
6. Thêm script kiểm khuôn chạy trong CI: báo thư mục/file ngoài danh sách ở bước 2 và chuỗi prompt viết cứng (`"""Bạn là…`, `INSTRUCTIONS = """`) trong `core/`.

Chuyển code theo từng domain trong [ISSUE-023](../../issues/10-2026/ISSUE-023-khuon-domain-core/issue.md), làm sau khi bug-042 merge.

## Các phương án đã cân nhắc

**Lưu trữ prompt**

| Phương án | Vì sao không chọn |
|---|---|
| Gom mọi prompt/text vào một `prompts.yaml` | Regex trong YAML dễ escape sai; trộn thứ có nhịp đổi khác nhau; một file nhiều người sửa dễ conflict; không version từng prompt |
| Hằng Python `app/core/prompts.py` | Mất version + hash; bỏ cơ chế file đang chạy cho Copilot |
| Lưu DB, admin sửa trên platform | Cần audit, phân quyền, chống sửa bậy; quá tay cho đồ án |
| Chỉ dọn chỗ trùng | Prompt eval vẫn viết cứng, không có luật chặn tái phát |

**Khuôn module**

| Phương án | Vì sao không chọn |
|---|---|
| Giữ cứng ba thư mục, dồn hết vào `engines/` | `engines/` thành ngăn kéo tạp; câu trả lời mẫu hay hằng số không phải thuật toán |
| Tổ chức theo use case toàn bộ `core/` | Đập lại mọi import ở `api/`; quá lớn cho giai đoạn này |
| Chỉ viết luật + script, không chuyển code | Code cũ vẫn lệch, chỉ chặn được lệch mới |

**Tên domain**

| Phương án | Vì sao không chọn |
|---|---|
| Domain theo năng lực (`core/anpr`, `core/rag`) | Phải đổi/tách proto service; `anti_fraud`, `vehicle_classifier` không có chỗ; `rag` chồng lấn `knowledge` |
| Lồng hai tầng `core/<domain>/<năng-lực>/{dtos,engines,services}` | Quá sâu khi mỗi domain chỉ 1–3 service |

## Hệ quả

### Được

- Mỗi loại thứ có đúng một chỗ, tên thư mục nói nó chứa gì; `api/` ↔ `core/` vẫn 1–1 theo gRPC service.
- Cả ba prompt (Copilot, judge, generator) có version + hash trong telemetry; xoá bốn cặp trùng.
- Đổi câu trả lời mẫu mà quên marker thì test eval đỏ ngay (test hợp đồng ở `test_knowledge_eval.py`).
- `script/check_core_layout.py` chạy trong CI chặn lệch mới.

### Đánh đổi

- Đụng khoảng 60 file (code, test, script, docs). Đã làm cuốn chiếu 5 chặng, mỗi chặng chạy đủ unittest.
- Nhánh đang mở chạm các file đã chuyển (`llm_factory.py`, `rag_pipeline.py`, `output_guard.py`, `anpr_engine.py`…) phải rebase và đổi đường dẫn import.
- Còn hai ngoại lệ ghi ở mục 3 (`parquet_lake_reader`, `dispute/fixtures.py`) chờ việc tiếp theo.

## Bằng chứng và liên kết

- [AI_CONVENTIONS §2](../../../standards/AI_CONVENTIONS.md#2-khuôn-một-domain-trong-core): luật ngắn trỏ về ADR này
- [ISSUE-023](../../issues/10-2026/ISSUE-023-khuon-domain-core/issue.md): kế hoạch và kết quả chuyển từng domain
- [bug-042](../../bugs/bug-042-prompt-copilot-khong-vao-image-chay-prompt-du-phong/bug.md): prompt không vào image, chạy prompt dự phòng (PR #112, merge 2026-10-28)
- [ADR-0002](0002-tu-choi-khi-thieu-ngu-canh.md): từ chối khi thiếu ngữ cảnh; `NO_CONTEXT_ANSWER` và marker là hợp đồng của quyết định đó
