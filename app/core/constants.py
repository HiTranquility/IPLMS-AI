"""Hằng số dùng chung cho toàn bộ domain AI."""

# ── Vision ────────────────────────────────────────────────────────────────────
FALLBACK_PLATE_NUMBER = "UNKNOWN"

# Ràng buộc biển số Việt Nam (tối đa 11 ký tự, ít nhất 1 chữ cái).
PLATE_MAX_LENGTH = 11
PLATE_MIN_ALPHA = 1
# Tối thiểu 6 ký tự chữ/số (bỏ dấu): biển ngắn nhất thật — quân sự `TM-12-34` —
# có 6. Ngắn hơn là mảnh đọc sót ("A", "7A"), không được trả như một biển số.
PLATE_MIN_ALNUM = 6
# EasyOCR (vi) đọc được chữ có dấu/ký hiệu; biển số chỉ có các ký tự này.
PLATE_OCR_ALLOWLIST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-."

# ── Forecast ──────────────────────────────────────────────────────────────────
FORECAST_SLOT_SECONDS = 1800  # 30 phút
DEFAULT_FORECAST_HOURS = 4

# ── Anti-Fraud ────────────────────────────────────────────────────────────────
# Điểm tương đồng ảnh khi CHƯA có phép đo nào. Cùng quy ước với `confidence` của
# ANPR: 0.0 nghĩa là "không có cơ sở để tin", không phải "đo ra 0%".
#
# [NEVER] khai lại hằng số kiểu `FRAUD_SIMILARITY_PASS = 0.98`. Bản cũ có hai
# hằng như vậy và chúng khiến mọi response trông như đã qua một phép đo thị giác
# — trong khi phép so ảnh crop (ReID) chưa hề được triển khai.
SIMILARITY_NOT_MEASURED = 0.0

# ── Knowledge / RAG ───────────────────────────────────────────────────────────
# Trần kích thước tài liệu owner tải lên.
# [GOTCHA] Phải THẤP HƠN `grpc_max_message_length` (đang là đúng 10MB, xem
# server_config.py): file 10MB cộng thêm phần khung message + các field khác sẽ
# vượt trần và bị gRPC chặn thẳng, lỗi báo ra lại khó hiểu với người dùng cuối.
KNOWLEDGE_MAX_FILE_BYTES = 8 * 1024 * 1024

# Trần thời gian cho cả lượt parse tài liệu (giây) — hạn trả lời cho request.
# [GOTCHA] Nó KHÔNG dừng được parser bị treo: tầng service dùng wait_for(to_thread),
# Python không giết được thread. Phần chống DoS thật (pypdf có 6 CVE năm 2026 dạng
# "PDF crafted khiến parser treo / ngốn RAM") là PDF_TEXT_TIMEOUT_SECONDS bên dưới:
# bước pypdf chạy trong process con và bị giết khi quá hạn.
# 120s vì PDF scan phải OCR: đo 2026-10-08 ~6–15s/trang trên CPU + ~26s nạp model
# lần đầu → 6 trang (_PDF_OCR_MAX_PAGES) tệ nhất ~116s (bug-026). Giữ < 150s
# deadline gRPC của backend, < 155s frontend, < 180s nginx — nâng ở đây thì nâng cả chuỗi.
DOCUMENT_PARSE_TIMEOUT_SECONDS = 120.0

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
