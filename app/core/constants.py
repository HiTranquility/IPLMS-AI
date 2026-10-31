"""Hằng số dùng chung cho toàn bộ domain AI."""

# ── Vision ────────────────────────────────────────────────────────────────────
FALLBACK_PLATE_NUMBER = "UNKNOWN"
# Luật chuỗi biển số chỉ vision dùng: app/core/vision/constants.py (ADR-0005).
# Trần một ảnh ANPR gửi qua REST (bug-043). Cùng mức 8MB với ANPR thử ở Console;
# thấp hơn `grpc_max_message_length` (10MB) để ảnh qua REST cũng đi được gRPC.
# Dùng chung cho `/anpr/*` và `/vision/recognize` (app/api/rest/image_upload.py),
# nên nằm ở đây chứ không ở app/core/vision/constants.py (bug-050).
ANPR_MAX_IMAGE_BYTES = 8 * 1024 * 1024
# Trần số ảnh mỗi request `/anpr/recognize-many` (bug-044): mỗi ảnh chạy YOLO + OCR
# tuần tự trên CPU dùng chung với đường nóng gRPC.
ANPR_MAX_FILES_PER_REQUEST = 10


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

