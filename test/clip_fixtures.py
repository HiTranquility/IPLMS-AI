"""Clip tổng hợp cho test đọc biển số từ video (IPLMS REQ-021 A).

Chưa có bộ clip thật của bãi: clip ở đây vẽ từng "xe" (khối màu riêng + biển số
từ `demo_plate_generator`) chạy ngang khung hình, xe sau vào khi xe trước đã ra
hẳn. Màu thân xe là định danh để bộ nhận diện giả trong test biết xe nào đang ở
trong khung mà không cần model.

Chạy tay để có file thử trên UI:  python -m test.clip_fixtures var/sample-3-cars.mp4
"""
import os
import sys
import tempfile
from typing import Dict, Optional, Sequence, Tuple

import cv2
import numpy as np

from app.core.console.engines.demo_plate_generator import generate_plate_image

FRAME_W, FRAME_H = 960, 540
CAR_W, CAR_H = 420, 260
# (biển số, màu thân xe BGR) — màu đủ xa nhau để phân biệt bằng trung bình kênh.
CARS: Tuple[Tuple[str, Tuple[int, int, int]], ...] = (
    ("51A-888.88", (40, 40, 200)),
    ("30E-123.45", (40, 180, 40)),
    ("15A-345.67", (200, 60, 40)),
)


def _car_sprite(plate: str, color: Tuple[int, int, int]) -> np.ndarray:
    car = np.full((CAR_H, CAR_W, 3), color, np.uint8)
    plate_img = cv2.imdecode(np.frombuffer(generate_plate_image(plate), np.uint8), cv2.IMREAD_COLOR)
    plate_img = cv2.resize(plate_img, (220, 80))
    y, x = CAR_H - 100, (CAR_W - 220) // 2
    car[y:y + 80, x:x + 220] = plate_img
    return car


def build_clip(
    cars: Sequence[Tuple[str, Tuple[int, int, int]]] = CARS,
    fps: int = 10,
    pass_s: float = 3.0,
    gap_s: float = 2.0,
    suffix: str = ".mp4",
) -> bytes:
    """Trả bytes clip: mỗi xe chạy ngang trong `pass_s` giây, nghỉ `gap_s` giữa hai xe."""
    fourcc = cv2.VideoWriter_fourcc(*("VP80" if suffix == ".webm" else "mp4v"))
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        writer = cv2.VideoWriter(path, fourcc, fps, (FRAME_W, FRAME_H))
        background = np.full((FRAME_H, FRAME_W, 3), 70, np.uint8)
        pass_frames, gap_frames = int(pass_s * fps), int(gap_s * fps)
        for plate, color in cars:
            sprite = _car_sprite(plate, color)
            for i in range(pass_frames):
                frame = background.copy()
                x = int(i * (FRAME_W - CAR_W) / max(1, pass_frames - 1))
                y = (FRAME_H - CAR_H) // 2
                frame[y:y + CAR_H, x:x + CAR_W] = sprite
                writer.write(frame)
            for _ in range(gap_frames):
                writer.write(background)
        writer.release()
        with open(path, "rb") as fh:
            return fh.read()
    finally:
        os.remove(path)


def fake_recognizer(cars: Sequence[Tuple[str, Tuple[int, int, int]]] = CARS, misread_every: int = 0):
    """Bộ nhận diện giả: tìm khối màu thân xe, trả biển của xe đó + bbox vùng biển.

    `misread_every > 0`: cứ mỗi lần thứ N đọc sai một ký tự, như OCR thật trên frame mờ.
    """
    calls: Dict[str, int] = {"n": 0}

    def recognize(jpeg: bytes) -> Dict:
        frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR).astype(np.int16)
        for plate, color in cars:
            mask = (np.abs(frame - np.array(color, np.int16)).sum(axis=2) < 60)
            ys, xs = np.nonzero(mask)
            if len(xs) < 2000:
                continue
            calls["n"] += 1
            x1, y2 = int(xs.min()), int(ys.max())
            cx = (x1 + int(xs.max())) // 2
            text = plate
            if misread_every and calls["n"] % misread_every == 0:
                text = plate[:-1] + ("0" if plate[-1] != "0" else "1")
            return {"plate_number": text, "confidence": 0.9, "crop_bytes": b"crop-" + plate.encode(),
                    "plate_bbox": [cx - 110, y2 - 100, cx + 110, y2 - 20]}
        return {"plate_number": "UNKNOWN", "confidence": 0.0, "crop_bytes": b"", "plate_bbox": None}

    return recognize


if __name__ == "__main__":
    out: Optional[str] = sys.argv[1] if len(sys.argv) > 1 else None
    if not out:
        sys.exit("usage: python -m test.clip_fixtures <out.mp4|out.webm>")
    with open(out, "wb") as fh:
        fh.write(build_clip(suffix=os.path.splitext(out)[1] or ".mp4"))
    print(out)
