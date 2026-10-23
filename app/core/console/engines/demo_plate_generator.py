"""Tạo ảnh biển số xe Việt Nam mẫu phục vụ môi trường thực hành / sandbox (ISSUE-126).

Hỗ trợ các dạng biển số thực tế:
- Ô tô cá nhân biển trắng (51A-888.88)
- Xe máy 2 dòng biển vuông (29-B1 999.99)
- Xe kinh doanh vận tải / taxi biển vàng (30E-123.45)
- Xe điện cá nhân (60-A 888.88)
- Biển chụp lệch / mờ cần gán sửa (43A-567.89)
"""
from __future__ import annotations

import io
from PIL import Image, ImageDraw, ImageFont

# Capture id cố định để nạp lại không nhân bản mẫu. `seed_label` là nhãn do một
# thành viên KHÁC người bấm nạp tạo sẵn, để người bấm có nhãn mà thực hành duyệt.
DEMO_SAMPLES: tuple[dict, ...] = (
    {"capture_id": "a0000000-0000-0000-0000-000000000001", "plate": "51A-888.88", "machine_plate": "51A-888.88",
     "machine_confidence": 0.97, "human_corrected": False, "selection_reasons": ["random_audit"],
     "type": "car", "two_line": False, "seed_label": None},
    {"capture_id": "a0000000-0000-0000-0000-000000000002", "plate": "29-B1 999.99", "machine_plate": "29-B1 999.99",
     "machine_confidence": 0.88, "human_corrected": False, "selection_reasons": ["two_line_plate", "low_confidence"],
     "type": "moto", "two_line": True, "seed_label": None},
    {"capture_id": "a0000000-0000-0000-0000-000000000003", "plate": "30E-123.45", "machine_plate": "30E-123.45",
     "machine_confidence": 0.93, "human_corrected": False, "selection_reasons": ["commercial_taxi"],
     "type": "taxi", "two_line": False, "seed_label": None},
    {"capture_id": "a0000000-0000-0000-0000-000000000004", "plate": "60-A 888.88", "machine_plate": "60-A 888.88",
     "machine_confidence": 0.95, "human_corrected": False, "selection_reasons": ["electric_vehicle"],
     "type": "electric", "two_line": False, "seed_label": None},
    {"capture_id": "a0000000-0000-0000-0000-000000000005", "plate": "43A-567.89", "machine_plate": "43A-567.80",
     "machine_confidence": 0.64, "human_corrected": True, "selection_reasons": ["low_confidence", "staff_corrected"],
     "type": "car", "two_line": False, "seed_label": None},
    {"capture_id": "a0000000-0000-0000-0000-000000000006", "plate": "15A-345.67", "machine_plate": "15A-345.67",
     "machine_confidence": 0.92, "human_corrected": False, "selection_reasons": ["random_audit"],
     "type": "car", "two_line": False,
     "seed_label": {"label_id": "b0000000-0000-0000-0000-000000000006", "verdict": "CORRECT", "plate_text": "15A-345.67"}},
    {"capture_id": "a0000000-0000-0000-0000-000000000007", "plate": "59-X3 789.01", "machine_plate": "59-X3 789.00",
     "machine_confidence": 0.72, "human_corrected": True, "selection_reasons": ["low_confidence", "mismatch"],
     "type": "moto", "two_line": True,
     "seed_label": {"label_id": "b0000000-0000-0000-0000-000000000007", "verdict": "CORRECTED", "plate_text": "59-X3 789.01"}},
)


def generate_plate_image(text: str, plate_type: str = "car", two_line: bool = False) -> bytes:
    """Tạo byte JPEG của ảnh crop biển số xe chuẩn Việt Nam."""
    width, height = (440, 160) if not two_line else (360, 240)
    bg_bumper = (30, 41, 59)  # Slate-800 viền cản xe
    img = Image.new("RGB", (width, height), bg_bumper)
    draw = ImageDraw.Draw(img)

    pad = 14
    rect = [pad, pad, width - pad, height - pad]

    text_color = (15, 23, 42)
    # Vàng: biển kinh doanh vận tải; còn lại nền trắng.
    surface_color = (250, 204, 21) if plate_type == "taxi" else (255, 255, 255)

    # Viền ngoài biển số
    draw.rounded_rectangle(rect, radius=12, fill=surface_color, outline=(15, 23, 42), width=6)
    # Viền chỉ chìm bên trong
    draw.rounded_rectangle(
        [pad + 5, pad + 5, width - pad - 5, height - pad - 5],
        radius=8,
        outline=(148, 163, 184) if plate_type != "taxi" else (202, 138, 4),
        width=2,
    )

    if two_line:
        font = ImageFont.load_default(size=42)
        parts = text.split(" ") if " " in text else [text[:5], text[5:].lstrip("-")]
        draw.text((width // 2, height // 2 - 32), parts[0], fill=text_color, font=font, anchor="mm")
        draw.text(
            (width // 2, height // 2 + 32),
            parts[1] if len(parts) > 1 else "",
            fill=text_color,
            font=font,
            anchor="mm",
        )
    else:
        font = ImageFont.load_default(size=46)
        draw.text((width // 2, height // 2), text, fill=text_color, font=font, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()
