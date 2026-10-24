# 🐛 bug-018: Console hiện kết quả bịa khi API lỗi hoặc không tồn tại (ANPR, tranh chấp, chẩn đoán, model, forecast)

> **Đích:** `docs/projects/bugs/bug-018-ui-bia-ket-qua-khi-api-loi/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | ✅ Fixed — merge vào develop qua HiTranquility/IPLMS-AI#51 (2026-10-24) — nhánh `bugfix/bug-017-2026-10-chat-studio-contract` (gom cùng bug-017, chủ dự án duyệt) |
| **Môi trường** | `develop@5f8e753`; các phần này vào cùng [ISSUE-003](../../issues/10-2026/ISSUE-003-console-root-routing-copilot-studio/issue.md) |

## Hành vi thực tế

Bảy chỗ trong `ai/ui` hiện số liệu hoặc kết quả "thành công" không đến từ server. Không chỗ nào có nhãn cho người xem biết đó là mô phỏng:

| # | Màn hình | Chuyện gì xảy ra | Vị trí |
|---|---|---|---|
| 1 | Vision → ANPR Sandbox | Gọi `POST /api/anpr/recognize`. Console không có route này (chỉ process inference có), nên lần gọi luôn hỏng. UI khi đó "nhận diện" ra biển của preset với **confidence 0.985** | `ui/src/pages/Vision/components/AnprSandbox/AnprSandbox.tsx:319, 352-360` |
| 2 | Vision → Anti-Fraud | `POST /api/vision/verify-match`: route này nằm trên process inference, đi sau `require_developer_access`, nên console luôn trả 404. Khi server trả kết quả thật nhưng thiếu `similarity_score`, UI tự điền 0.982 hoặc 0.12 | `AnprSandbox.tsx:398-425` |
| 3 | Copilot → Dispute Simulator | Không dùng kết quả server, kể cả khi server trả `steps`. Luôn hiện 5 bước cố định, kết thúc ở `RESOLVED_REFUNDED`, có `wallet_tx_id` và `audit_log_hash` viết sẵn trong code | `ui/src/pages/Copilot/components/ChatStudio/DisputeSimulator.tsx:150-200` |
| 4 | Copilot → Knowledge Explorer | `GET /knowledge/seeds` không tồn tại. UI im lặng hiện `DEFAULT_SEED_DOCUMENTS` như thể đó là kho tri thức thật | `KnowledgeExplorer.tsx:36, 51-66` |
| 5 | Công cụ thử → Chẩn đoán | YOLO "READY 14.2 MB bootstrap-v1", EasyOCR "CACHED", PyTorch 2.6.0, CUDA False đều là hằng số. Chỉ `vision_device` lấy từ `/tools/system`. Nút "Làm mới" không đổi được các số này | `ui/src/pages/Tools/components/SystemDiagnostics/SystemDiagnostics.tsx:35-48`; [ảnh](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/04-tools.png) chụp khi mock API không trả các trường đó |
| 6 | Model & lượt đo → Đăng ký | "Kiểm tra kết nối" không gọi mạng: chờ 350 ms rồi báo "Endpoint phản hồi 16ms, checksum hợp lệ". 3 preset có `s3://` không tồn tại và sha256 bịa (một mã là sha256 của chuỗi rỗng), mô tả "độ chính xác 99.2%", "độ trễ 12ms" | `ui/src/pages/Vision/components/RegisterModelForm.tsx:20-45, 83-105` |
| 7 | Công cụ thử → Dự báo & giá động | Đường lấp đầy 24 giờ lấy từ hằng `LOT_OCCUPANCY_BASELINES`. "Doanh thu ước tính" tính bằng hệ số `2.28` không có nguồn. Forecast server vẫn là `FeatureNotImplementedError` | `ui/src/pages/Tools/components/ForecastSimulator/ForecastSimulator.tsx:57-80` |

Ngay trên trang Công cụ thử có thẻ "Thà lỗi hơn bịa (ADR-0008)", nhưng các chỗ trên làm ngược lại điều đó.

## Hành vi mong đợi

Theo `ui/DESIGN.md:71` ("Không bịa số: không có dữ liệu thì `—` hoặc empty state nói rõ lý do") và nguyên tắc "Thà lỗi hơn bịa" (`docs/guides/09-2026/01-three-ai-pipelines-architecture.md:78`):

- API lỗi hoặc không tồn tại → UI báo lỗi hoặc hiện empty state, không đưa ra kết quả.
- Phần cố ý mô phỏng để demo → nhãn "MÔ PHỎNG — không phải kết quả model" luôn hiện, có cờ bật hoặc tắt, và không bao giờ hiện confidence hay chỉ số dưới dạng số thật.
- Gọi API qua `services/apiEndpoints` và `apiClient`, không `fetch` thẳng với `apiBase` tự đoán.

## Tái hiện

1. Chạy UI dev (`pnpm --dir ui dev`) với một API giả trả 404 cho mọi route ngoài `/console/api/*` đã khai. Bản dùng trong lượt rà này: [mock_console_api.py](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/mock_console_api.py).
2. Vào Công cụ thử: thẻ YOLO hiện "READY, 14.2 MB" dù API không trả các trường đó.
3. Đọc các vị trí ở bảng trên. Mục 1-4 rơi vào nhánh fallback vì route không có trên console (`app/console_main.py:75-83` chỉ gắn `console_router`).

## Bằng chứng

Xem bảng (`file:line`) và ảnh `evidence/04-tools.png`. Test UI hiện có đều mock `fetch` nên không bắt được lỗi này.

## Sửa / kiểm chứng

Chủ dự án chốt OPEN-03 ngày 2026-10-24: API lỗi thì báo lỗi thật, không bịa số; studio chưa có API thật vẫn giữ nhưng luôn gắn nhãn **MÔ PHỎNG**.

Thêm component dùng chung `ui/src/components/common/Ui/feedback/SimulatedBanner.tsx`. Nhãn cố định, không tắt được, màu theo token, chữ qua i18n (`simulated.*`, VI+EN). Đường API của các studio gom vào `ui/src/services/apiEndpoints/studio.endpoint.ts` và gọi qua `apiClient` (kiểu ở `ui/src/types/tool/shares/studio.item.ts`). Tới nay console chưa gắn các route đó nên sẽ nhận 404 và UI báo lỗi. Khi backend thêm route thì UI dùng được ngay.

| # | Chỗ | Sửa |
|---|---|---|
| 1 | ANPR Sandbox | `AnprSandbox.tsx:302`: gọi `recognizePlate` (`/console/api/anpr/recognize`). Lỗi → `ErrorBlock`, không dựng biển từ preset, bỏ 0.985/0.978. Trường thiếu (confidence, màu biển, event, thời gian) hiện "—". Bỏ badge "CNN NetV2 Active" (ghi "Máy chủ chưa báo"). Banner MÔ PHỎNG ở `:400` |
| 2 | Anti-Fraud | `AnprSandbox.tsx:337`: gọi `verifyMatch`. Lỗi → `ErrorBlock`, không tự so hai ô chọn rồi gán 0.985/0.124. `similarity_score` thiếu → "—" |
| 3 | Dispute Simulator | `DisputeSimulator.tsx:84`: chỉ hiện `steps` server trả, rỗng/lỗi → `ErrorBlock`. Bỏ 5 bước cố định, `wallet_tx_id`, `audit_log_hash`, câu "cần Giám sát duyệt hoàn tiền theo Điều 5" gài sẵn khi gửi sang chat. Số node lấy theo `steps.length` |
| 4 | Knowledge Explorer | `KnowledgeExplorer.tsx:58`: danh sách chỉ từ `/knowledge/seeds`; lỗi → rỗng + `ErrorBlock`. Xoá `defaultSeeds.ts`, bỏ "pgvector: Sẵn sàng". Sửa thêm: nạp bản nháp gửi `document_id = doc_<timestamp>` nên server (đòi UUID) luôn trả 422; nay dùng `crypto.randomUUID()` và `ingestDraft` của `apiClient` (`:123`) |
| 5 | Chẩn đoán | `SystemDiagnostics.tsx:24`: chỉ `vision_device` từ `/tools/system`. YOLO/EasyOCR/PyTorch/CUDA hiện "—", badge "Máy chủ chưa báo", kèm ghi chú. API lỗi → `ErrorBlock`. Gỡ 10 khoá i18n trạng thái không còn dùng |
| 6 | Đăng ký model | `RegisterModelForm.tsx:24`: xoá 3 preset (s3 giả, sha256 bịa, "99.2%", "12ms") và CSS preset. "Kiểm tra kết nối" giả 350 ms → "Kiểm tra định dạng", nói rõ chỉ kiểm cục bộ |
| 7 | Dự báo & giá động | `ForecastSimulator.tsx:124`: banner MÔ PHỎNG; đường lấp đầy đổi nhãn thành "Kịch bản minh hoạ" và mô tả nói rõ chưa có model. "Biến động doanh thu" (hệ số 2.28) → "—", "chưa có mô hình doanh thu" (`:278`) |
| + | Chat Studio header | `ChatStudio.tsx:53`: tên model lấy từ `/tools/system` thay cho chuỗi "Copilot RAG v2.4"; chọn preset tham số không còn đổi tên model trên header |

**Kiểm chứng (2026-10-24):** `pnpm typecheck` PASS. `npx vitest run --maxWorkers=1`: 13 file / 57 test PASS, trước là 48. Các ca "API 404 → không hiện kết quả bịa" và "API trả dữ liệu → hiện đúng dữ liệu đó" có cho từng chỗ: `ChatStudio.test.tsx` (Knowledge, Dispute), `AnprSandbox.test.tsx` (ANPR, Anti-Fraud), `SystemDiagnostics.test.tsx`, `ForecastSimulator.test.tsx`, `RegisterModelForm.test.tsx` (mới).

**Nối API thật (2026-10-24, chủ dự án: "nối API thật vào"):** ba studio có service thật thì gọi thẳng service đó trong process console (ADR-0048 §1), bỏ banner MÔ PHỎNG:

| Studio | Route console mới | Service thật | Quyền |
|---|---|---|---|
| ANPR Sandbox | `POST /tools/anpr/recognize` (multipart, ≤ 8 MB) | `AnprService.recognize_bytes(persist_files=False)`: engine đang nạp, không lưu ảnh (PII) | `ai:model:evaluate` |
| Anti-Fraud | `POST /tools/vision/verify-match` (chỉ 2 loại xe, `extra="forbid"`) | `anti_fraud_service.verify_vehicle_match`. Service chưa so ảnh, nên `similarity_score` trả `null` thay vì hằng `0.0` | `ai:model:evaluate` |
| Knowledge Explorer | `GET /tools/knowledge/documents` | `ingestion_service.list`: metadata thật (số đoạn, phiên bản mới nhất, bản khách đang thấy) | `ai:prompt:edit` |
| Chẩn đoán | `/tools/system` thêm `engines` | Đường dẫn và dung lượng weights YOLO đọc từ đĩa, phiên bản, YOLO/EasyOCR đã nạp hay chưa (đọc bộ nhớ process, không nạp model), ngôn ngữ OCR, phiên bản torch (metadata gói), CUDA chỉ khi torch đã nạp sẵn. Không biết chắc thì `null` → "—" | `ai:metrics:read` |

Code: `app/core/console/services/tools_service.py` (`_engine_status`, `try_anpr`, `verify_match`, `knowledge_documents`), `app/api/rest/routes/console_tools_controller.py`. UI: `studio.endpoint.ts`, kiểu trong `studio.item.ts`/`tool.response.ts`, `SystemDiagnostics.tsx`, `KnowledgeExplorer.tsx` (thẻ hiện metadata thật), `AnprSandbox.tsx`.

Kiểm: `python -m unittest test.test_console_tools` (thêm `StudioRealApiTest`: engine được gọi với `persist_files=False`, quyền, ảnh rỗng, điểm chưa đo là `null`, map tài liệu, weights thiếu → `null`) + `test_console_copilot_lab test_rag_pipeline test_llm_factory`: PASS. UI typecheck PASS, vitest 59/59 PASS.

**Còn lại:**
- Mô phỏng tranh chấp vẫn MÔ PHỎNG. Workflow LangGraph (ai ISSUE-001) chưa có `EvidenceClient`/bộ nạp bằng chứng thật nên chưa có gì để nối (việc của Dương). Route `/dispute-workflow/simulate` ở process inference (`copilot_controller.py:248`) vẫn trả bước viết sẵn.
- Forecast vẫn là "Kịch bản minh hoạ": server còn `FeatureNotImplementedError`.
- Anti-Fraud so ảnh (ReID, SUGGESTION-007 B6) chưa có, nên độ tương đồng luôn "—".
- Chưa chạy ANPR thật trên máy có weights; test dùng engine giả lập.
