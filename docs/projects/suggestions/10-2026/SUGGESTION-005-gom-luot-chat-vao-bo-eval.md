# 🌱 SUGGESTION-005: Đưa lượt chat đã chấm thành ca hồi quy và so A/B phiên bản prompt ngay trong Copilot Lab

> **Đích:** `docs/projects/suggestions/10-2026/SUGGESTION-005-gom-luot-chat-vao-bo-eval.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🔄 REVIEWING |
| **Ưu tiên** | 🟢 |
| **Ngày** | 2026-10-23 |
| **Người đề xuất** | Claude Code ([ISSUE-004](../../issues/10-2026/ISSUE-004-ai-console-ui-review/issue.md)) |
| **Techlead duyệt** | @HiTranquility — ⏳ chờ |
| **Làm trước khi duyệt?** | Không: thêm API và bảng |
| **Phạm vi** | `ai/` (Copilot Lab, bộ held-out của IPLMS ISSUE-126 review-7) |

## Đề xuất

1. Ở Copilot Lab, lượt đã chấm **Sai** hoặc **Không an toàn** có nút "Thêm vào bộ hồi quy". Nút này lưu câu hỏi (đã che PII), kết luận và ghi chú của người chấm thành một ca eval có nhãn, có phiên bản.
2. Thêm trang "So sánh" chạy bộ hồi quy trên 2 `prompt_version` hoặc 2 model, hiện tỉ lệ đúng, tỉ lệ từ chối nhầm và độ trễ p95 cạnh nhau. Chạy qua Router nội bộ, không gọi thẳng nhà cung cấp LLM.

## Vấn đề nó giải quyết

Mô tả trang Copilot Lab đã hứa "gom ca vào bộ eval", nhưng UI chưa có nút nào làm việc đó. Dương đang mở rộng bộ held-out lên ≥ 30 câu bằng tay, còn Khoa cần số liệu trước/sau khi đổi ngưỡng similarity. Hai việc này dùng chung được một công cụ.

## Phạm vi

- Trong: lưu ca, chạy so sánh, hiện kết quả.
- Ngoài: tự sửa prompt.

## Bằng chứng / tham khảo

- Mô tả trang ở [ảnh](../../issues/10-2026/ISSUE-004-ai-console-ui-review/evidence/03-copilot.png).
- BOARD: Dương mục 1, Khoa mục 3.

## Bước tiếp theo

Khoa và Dương thống nhất định dạng ca eval, rồi mở ISSUE. Phần UI giao Phát.
