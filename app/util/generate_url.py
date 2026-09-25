def sanitize_plate(plate_number: str) -> str:
    """Loại ký tự không hợp lệ để tên file an toàn."""
    safe = "".join(c for c in (plate_number or "") if c.isalnum() or c in ("-", "_"))
    return safe.replace(" ", "_") or "unknown"


def generate_original_image_url(plate_number: str, event_id: str) -> str:
    return f"/static/original/{sanitize_plate(plate_number)}_{event_id}.jpg"


def generate_cropped_image_url(plate_number: str, event_id: str) -> str:
    """Tên file PHẢI kèm event_id.

    Chỉ dùng biển số là đụng nhau: mọi xe không đọc được biển đều rơi về
    `FALLBACK_PLATE_NUMBER` nên sẽ ghi đè chung một file, và `VerifyVehicleMatch`
    lúc check-out sẽ đối chiếu nhầm ảnh của xe khác. Cùng một biển vào bãi nhiều
    lượt cũng vậy.
    """
    return f"/static/cropped/{sanitize_plate(plate_number)}_{event_id}_crop.jpg"
