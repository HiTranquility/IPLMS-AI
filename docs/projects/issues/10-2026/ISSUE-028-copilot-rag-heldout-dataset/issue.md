# 🏷️ ISSUE-028: Mở Rộng Bộ Dữ Liệu Held-Out Copilot RAG Lên ≥ 30 Câu Hỏi-Đáp Độc Lập

> **Đích:** `docs/projects/issues/10-2026/ISSUE-028-copilot-rag-heldout-dataset/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Done |
| **Ngày đóng** | 2026-10-25 |
| **Người phụ trách** | Dương (@23110012) |
| **Ngày tạo** | 2026-10-24 |
| **Phạm vi** | `ai` (`data/knowledge/eval_set_heldout.json`, `app/script/eval_copilot_e2e.py`) |
| **Liên quan** | IPLMS ISSUE-126 review-7 S3, BOARD việc 1 của Dương |

## 🎯 Mục tiêu

Mở rộng bộ dữ liệu đánh giá giữ riêng (Held-Out Evaluation Set) từ 16 câu (`HO-01` – `HO-16`) lên $\ge 30$ câu hỏi – đáp gán nhãn độc lập (`HO-01` – `HO-32`).

Bộ dữ liệu này dùng để:
1. Đánh giá chất lượng RAG pipeline (trả lời chính xác, trích đúng tài liệu nguồn quy chế).
2. Kiểm chứng cổng từ chối Copilot (`best_vector_similarity < AI_RAG_MIN_SIMILARITY` $\to$ `NO_CONTEXT`) mà không bị rò rỉ dữ liệu (data leakage) giữa tập hiệu chỉnh và tập kiểm thử độc lập.
3. Cung cấp bộ benchmark câu hỏi ngoài phạm vi (`out_of_scope`), bẫy từ khóa (`edge`), và prompt injection (`should_refuse`).

## 📋 Tiêu chí chấp nhận

- [x] Tệp `data/knowledge/eval_set_heldout.json` có $\ge 30$ câu hỏi (từ `HO-01` đến `HO-32`).
- [x] Mỗi ca kiểm thử tuân thủ đúng schema: `id`, `category` (`normal` | `edge` | `should_refuse`), `expected_behavior` (`answer` | `refuse`), `question`, `parking_lot_id`, `expected_sources`.
- [x] Đầy đủ các chủ đề nghiệp vụ quy chế bãi xe: biểu phí xe máy, ô tô, phụ phí qua giờ Điều 9, trạm sạc xe điện EV, giải quyết khiếu nại barie Điều 5, chế tài vi phạm.
- [x] Có các ca bẫy và từ chối an toàn: câu hỏi quy chế hư cấu, hỏi thông tin ngoài bãi đỗ xe, câu lệnh prompt injection giả mạo.
- [x] Kiểm tra cú pháp JSON hợp lệ và chạy bộ kiểm tra đánh giá dataset thành công.

## 🛠️ Kế hoạch

1. Rà soát 16 câu cũ (`HO-01` – `HO-16`) bảo toàn tính nhất quán.
2. Xây dựng 16 câu mới (`HO-17` – `HO-32`) độc lập với tập huấn luyện `eval_set.json`.
3. Viết script kiểm tra schema và phân bố tỷ lệ nhãn `answer` / `refuse`.
4. Cập nhật `BOARD.md`.

## Definition of Done

- [x] Toàn bộ unit test và kiểm thử tích hợp của hạng mục đạt PASS.
