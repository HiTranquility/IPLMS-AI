# Tài liệu demo để thử nạp Knowledge Base & Trợ lý thông minh (ISSUE-009)

Nạp trên giao diện:
- **Operator (Chủ bãi / Quản lý):** Chi tiết bãi → tab **`📚 Quy Chế & Trợ Lý Thông Minh`** (cung cấp sẵn **Trình Quản Lý File Quy Chế Chuẩn `.md` / `.csv` / `.json`** + nút nạp 1-click có khoá chống spam 15 giây).
- **Client (Khách gửi xe):** Chi tiết bãi → khung **`Trợ lý thông minh · {Tên bãi}`** → nút **`📄 Xem quy chế bãi (.md)`**.
- **Platform (Admin / Moderator):** Kho tri thức AI (`scope = GLOBAL`).

## 1. Tài liệu hướng dẫn trình bày & bảo vệ đồ án
- **[`huong-dan-trinh-bay-rag-datalake-anti-ddos.md`](./huong-dan-trinh-bay-rag-datalake-anti-ddos.md)**: Kịch bản thuyết trình và hỏi-đáp phản biện toàn diện về:
  1. Quy trình 4 bước quản lý file quy chế `.md` ở từng bãi (`DRAFT` → `Test Suite` → `TESTED` → `PUBLISHED`).
  2. Bộ dữ liệu thực tế đã seed cho **toàn bộ 503 bãi đỗ xe** (`503` tài liệu `PUBLISHED`, `2.012` chunks, `3.018` câu test, `503` lượt chạy `PASSED`) và **150 file đa định dạng** cho 25 bãi trọng điểm tại [`samples-by-area/`](./samples-by-area/README.md).
  3. Cơ chế **7 lớp Chống DDoS / Chống Spam từ Chủ bãi** (Cooldown 15s, SHA-256 Content-Hash Deduplication, Magic-Bytes Sanitizer 8MB, Sliding-Window Rate Limit 15 lần/60s/bãi, `pg_advisory_xact_lock`, Deterministic Grader 0-token, Scoped Hybrid Retrieval).
  4. Luồng dữ liệu **Medallion Data Lake (`Bronze -> Silver -> Gold Parquet`)** với `338.016` dòng telemetry tại `ai/var/datalake/gold/occupancy/year=2026/month=11/all_503_areas_telemetry.parquet`.

## 2. Bộ file mẫu kiểm thử Parser & Security Gate

| File | Định dạng | Kết quả mong đợi |
|---|---|---|
| `01-quy-che-demo.md` | Markdown | Nạp được — 4 đoạn (Điều 1–4: biểu phí, qua đêm, quá giờ, khiếu nại) |
| `02-noi-quy-xe-may-demo.txt` | TXT | Nạp được — xe máy 5.000đ/lượt, mất vé 50.000đ (viết không dấu) |
| `03-bieu-phi-sac-ev-demo.docx` | Word | Nạp được — sạc 3.500đ/kWh, phí chiếm chỗ 15.000đ/30 phút |
| `04-an-ninh-demo.pdf` | PDF có lớp chữ | Nạp được — giờ mở cửa, hàng cấm (viết không dấu: font chuẩn PDF không có glyph tiếng Việt) |
| `90-ban-scan-khong-chu.pdf` | PDF không có chữ | **Bị từ chối** — "Tài liệu không có lớp văn bản — nhiều khả năng đây là bản scan…" |
| `91-gia-mao.pdf` | file .exe đổi đuôi | **Bị từ chối** — "Nội dung file không khớp phần mở rộng…" |
| [`samples-by-area/<area-id>/`](./samples-by-area/README.md) | `.md`, `.csv`, `.json`, `.txt`, `.docx`, `.pdf` | **150 file** của 25 bãi xe thực tế (6 định dạng/bãi) để demo nạp chéo hoặc tải về |

File > 8MB bị chặn ngay ở backend (không lưu mẫu vào repo). Không nhận `.doc` (Word 97–2003), `.xlsx`, ảnh.
