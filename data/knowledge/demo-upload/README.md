# Tài liệu demo để thử nạp Knowledge Base (ISSUE-009)

Nạp trên giao diện: operator → chi tiết bãi → tab "Quy Chế Cho AI Copilot" (owner), hoặc platform → "Kho tri thức AI" (admin/moderator). Cần `AI_LLM_API_KEY` để sinh embedding.

| File | Định dạng | Kết quả mong đợi |
|---|---|---|
| `01-quy-che-demo.md` | Markdown | Nạp được — 4 đoạn (Điều 1–4: biểu phí, qua đêm, quá giờ, khiếu nại) |
| `02-noi-quy-xe-may-demo.txt` | TXT | Nạp được — xe máy 5.000đ/lượt, mất vé 50.000đ (viết không dấu) |
| `03-bieu-phi-sac-ev-demo.docx` | Word | Nạp được — sạc 3.500đ/kWh, phí chiếm chỗ 15.000đ/30 phút |
| `04-an-ninh-demo.pdf` | PDF có lớp chữ | Nạp được — giờ mở cửa, hàng cấm (viết không dấu: font chuẩn PDF không có glyph tiếng Việt) |
| `90-ban-scan-khong-chu.pdf` | PDF không có chữ | **Bị từ chối** — "Tài liệu không có lớp văn bản — nhiều khả năng đây là bản scan…" |
| `91-gia-mao.pdf` | file .exe đổi đuôi | **Bị từ chối** — "Nội dung file không khớp phần mở rộng…" |

File > 8MB bị chặn ngay ở backend (không lưu mẫu vào repo). Không nhận `.doc` (Word 97–2003), `.xlsx`, ảnh.

Đã chạy qua parser + chunker thật trong container `ai` ngày 2026-09-25: đúng cả 6 file + file 8MB.
