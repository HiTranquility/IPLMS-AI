"""Hằng số chỉ domain knowledge dùng (ADR-0005). Hằng dùng chung nhiều domain ở `app/core/constants.py`."""

# Trần thời gian cho cả lượt parse tài liệu (giây) — hạn trả lời cho request.
# [GOTCHA] Nó KHÔNG dừng được parser bị treo: tầng service dùng wait_for(to_thread),
# Python không giết được thread. Phần chống DoS thật (pypdf có 6 CVE năm 2026 dạng
# "PDF crafted khiến parser treo / ngốn RAM") là PDF_TEXT_TIMEOUT_SECONDS bên dưới:
# bước pypdf chạy trong process con và bị giết khi quá hạn.
# 120s vì PDF scan phải OCR: đo 2026-10-08 ~6–15s/trang trên CPU + ~26s nạp model
# lần đầu → 6 trang (_PDF_OCR_MAX_PAGES) tệ nhất ~116s (bug-026). Giữ < 150s
# deadline gRPC của backend, < 155s frontend, < 180s nginx — nâng ở đây thì nâng cả chuỗi.
DOCUMENT_PARSE_TIMEOUT_SECONDS = 300.0

# Riêng bước pypdf đọc lớp chữ PDF (nơi có CVE treo parser) chạy trong process con
# và bị GIẾT khi quá hạn — timeout ở tầng service chỉ trả lỗi chứ không dừng được
# thread (bug-026). Đọc chữ PDF hợp lệ ≤ 8MB mất vài giây, kể cả ~1s khởi process.
PDF_TEXT_TIMEOUT_SECONDS = 30.0

# Cắt đoạn đo bằng KÝ TỰ chứ không phải token: đếm token đúng cần thêm `tiktoken`,
# một dependency nữa chỉ để làm mịn một ngưỡng vốn đã là áng chừng. Với tiếng Việt
# 1 token ≈ 2–3 ký tự, nên 1500 ký tự ≈ 500–700 token — đúng khoảng nhắm.
CHUNK_TARGET_CHARS = 1500
CHUNK_OVERLAP_CHARS = 200

# Đoạn ngắn hơn ngưỡng này bị bỏ: tiêu đề lẻ hay dòng trống sót lại không mang đủ
# ngữ cảnh để trả lời, nhưng vẫn tốn một lần gọi API embedding và một dòng DB.
CHUNK_MIN_CHARS = 100
