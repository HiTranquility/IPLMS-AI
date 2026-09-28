"""Hằng số dùng chung cho toàn bộ domain AI."""

# ── Vision ────────────────────────────────────────────────────────────────────
FALLBACK_PLATE_NUMBER = "UNKNOWN"

# Ràng buộc biển số Việt Nam (tối đa 11 ký tự, ít nhất 1 chữ cái).
PLATE_MAX_LENGTH = 11
PLATE_MIN_ALPHA = 1

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

# Trần thời gian cho một lượt parse tài liệu (giây). Không phải để tối ưu tốc độ
# mà để CHẶN DoS: pypdf đã có 6 CVE trong năm 2026 dạng "PDF crafted khiến parser
# treo vòng lặp vô hạn / ngốn sạch RAM". Ghim phiên bản chỉ chặn được CVE đã biết,
# trần thời gian chặn được cả loại chưa ai đặt tên.
DOCUMENT_PARSE_TIMEOUT_SECONDS = 60.0

# Cắt đoạn đo bằng KÝ TỰ chứ không phải token: đếm token đúng cần thêm `tiktoken`,
# một dependency nữa chỉ để làm mịn một ngưỡng vốn đã là áng chừng. Với tiếng Việt
# 1 token ≈ 2–3 ký tự, nên 1500 ký tự ≈ 500–700 token — đúng khoảng nhắm.
CHUNK_TARGET_CHARS = 1500
CHUNK_OVERLAP_CHARS = 200

# Đoạn ngắn hơn ngưỡng này bị bỏ: tiêu đề lẻ hay dòng trống sót lại không mang đủ
# ngữ cảnh để trả lời, nhưng vẫn tốn một lần gọi API embedding và một dòng DB.
CHUNK_MIN_CHARS = 100
