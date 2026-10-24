# 🐛 bug-018: Console hiện kết quả bịa khi API lỗi hoặc không tồn tại (ANPR, tranh chấp, chẩn đoán, model, forecast)

> **Đích:** `docs/projects/bugs/bug-018-ui-bia-ket-qua-khi-api-loi/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-23 / Claude Code, rà UI trong [ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md) |
| **Trạng thái** | 🆕 New / 🔴 sai im lặng ngay trên công cụ dùng để đánh giá AI |
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

Chưa sửa. Mỗi mục sửa xong cần một test "API 404 hoặc 500 → không hiện kết quả".
