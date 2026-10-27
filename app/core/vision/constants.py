"""Hằng số chỉ domain vision dùng (ADR-0005). Hằng dùng chung nhiều domain ở `app/core/constants.py`."""

# Ràng buộc biển số Việt Nam (tối đa 12 ký tự, ít nhất 1 chữ cái).
# Ví dụ: 59-V1-793.79 gồm 2 dấu gạch nối và 1 dấu chấm = 12 ký tự.
PLATE_MAX_LENGTH = 12
PLATE_MIN_ALPHA = 1
# Tối thiểu 6 ký tự chữ/số (bỏ dấu): biển ngắn nhất thật — quân sự `TM-12-34` —
# có 6. Ngắn hơn là mảnh đọc sót ("A", "7A"), không được trả như một biển số.
# Khác `_PLAUSIBLE_MIN_LEN = 7` trong anpr/plate_text.py: đó là điểm cộng mềm cho
# hình dạng thường gặp, còn đây là ngưỡng hợp lệ cứng.
PLATE_MIN_ALNUM = 6
# EasyOCR (vi) đọc được chữ có dấu/ký hiệu; biển số chỉ có các ký tự này.
PLATE_OCR_ALLOWLIST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-."
