"""Hằng số dùng chung cho toàn bộ domain AI."""

# ── Vision ────────────────────────────────────────────────────────────────────
FALLBACK_PLATE_NUMBER = "UNKNOWN"
# Luật chuỗi biển số chỉ vision dùng: app/core/vision/constants.py (ADR-0005).


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

