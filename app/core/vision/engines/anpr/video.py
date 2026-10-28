"""Đọc biển số từ clip (IPLMS REQ-021 hướng A): cắt frame → `run_anpr` → gộp theo xe.

Không lưu video gốc (F7): OpenCV chỉ mở được video từ đường dẫn, nên bytes clip
được ghi ra một file tạm và xoá ngay trong `finally` sau khi đọc xong frame. Kết
quả chỉ giữ ảnh cắt biển của frame tốt nhất mỗi sự kiện.

Gộp (F2): một lần đọc nhập vào sự kiện đang mở nếu cách lần thấy cuối không quá
`max_gap_s` VÀ (cùng `plate_key` HOẶC ô biển chồng lên nhau đủ `iou_threshold`).
IoU giữ các frame OCR đọc lệch một ký tự trong cùng một xe; khoảng cách thời gian
tách hai xe nối đuôi đỗ cùng một chỗ.
"""
import os
import tempfile
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterator, List, Optional, Tuple

import cv2
import numpy as np

from app.core.constants import FALLBACK_PLATE_NUMBER
from app.core.vision.engines.anpr.plate_text import plate_key

Bbox = Tuple[int, int, int, int]

CLIP_SUFFIXES = {"video/mp4": ".mp4", "video/webm": ".webm"}
# Ảnh thu nhỏ để so chuyển động: đủ thấy xe đi vào khung, rẻ hơn so ảnh gốc nhiều lần.
_MOTION_WIDTH = 160
# Một điểm ảnh tính là "đổi" khi lệch quá mức xám này — trên nhiễu nén, dưới tương phản xe/nền.
_MOTION_PIXEL_DELTA = 12


@dataclass(frozen=True)
class ClipLimits:
    max_duration_s: float
    max_frames: int
    sample_interval_s: float
    # None = cắt đều theo nhịp; có giá trị = chỉ giữ frame mà tỉ lệ điểm ảnh đổi
    # (so frame giữ trước đó) đạt ngưỡng này (0–1).
    motion_threshold: Optional[float] = None


@dataclass
class PlateRead:
    t: float
    plate_number: str
    confidence: float
    bbox: Optional[Bbox]
    crop_bytes: bytes


@dataclass
class PlateEvent:
    reads: List[PlateRead] = field(default_factory=list)

    @property
    def last(self) -> PlateRead:
        return self.reads[-1]

    def summary(self) -> Dict:
        # Biển của sự kiện = khoá có tổng điểm cao nhất; frame tốt nhất lấy trong khoá đó.
        score: Dict[str, float] = defaultdict(float)
        for read in self.reads:
            score[plate_key(read.plate_number)] += read.confidence
        winner = max(score, key=score.get)
        best = max((r for r in self.reads if plate_key(r.plate_number) == winner), key=lambda r: r.confidence)
        return {
            "plate_number": best.plate_number,
            "confidence": round(best.confidence, 4),
            "best_time_s": round(best.t, 2),
            "start_time_s": round(self.reads[0].t, 2),
            "end_time_s": round(self.last.t, 2),
            "frame_count": len(self.reads),
            "crop_bytes": best.crop_bytes,
        }


def iou(a: Optional[Bbox], b: Optional[Bbox]) -> float:
    if a is None or b is None:
        return 0.0
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def group_reads(reads: List[PlateRead], iou_threshold: float, max_gap_s: float) -> List[PlateEvent]:
    """Gộp các lần đọc (theo thứ tự thời gian) thành sự kiện, mỗi xe một sự kiện."""
    events: List[PlateEvent] = []
    for read in sorted(reads, key=lambda r: r.t):
        key = plate_key(read.plate_number)
        match = None
        for event in reversed(events):
            if read.t - event.last.t > max_gap_s:
                continue
            if plate_key(event.last.plate_number) == key or iou(event.last.bbox, read.bbox) >= iou_threshold:
                match = event
                break
        if match is None:
            match = PlateEvent()
            events.append(match)
        match.reads.append(read)
    return events


def _motion_signature(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (_MOTION_WIDTH, max(1, int(h * _MOTION_WIDTH / w))))
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.int16)


def iter_clip_frames(data: bytes, suffix: str, limits: ClipLimits) -> Iterator[Tuple[float, np.ndarray]]:
    """Trả `(giây, frame BGR)` theo nhịp `sample_interval_s`, lọc thêm theo chuyển động nếu bật.

    Raises:
        ValueError: clip không mở được, dài quá `max_duration_s`.
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="iplms-clip-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        cap = cv2.VideoCapture(path)
        try:
            if not cap.isOpened():
                raise ValueError("Không đọc được clip (chỉ nhận MP4/WebM).")
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
            # WebM thường không ghi số frame ở header: khi đó kiểm độ dài trong lúc đọc.
            if fps > 0 and frame_count > 0 and frame_count / fps > limits.max_duration_s:
                raise ValueError(f"Clip dài {frame_count / fps:.0f} giây, vượt giới hạn {limits.max_duration_s:.0f} giây.")
            next_t, kept, last_sig, index = 0.0, 0, None, 0
            while kept < limits.max_frames:
                ok, frame = cap.read()
                if not ok:
                    break
                t = index / fps if fps > 0 else cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                index += 1
                if t > limits.max_duration_s:
                    raise ValueError(f"Clip vượt giới hạn {limits.max_duration_s:.0f} giây.")
                if t + 1e-6 < next_t:
                    continue
                next_t = t + limits.sample_interval_s
                if limits.motion_threshold is not None:
                    sig = _motion_signature(frame)
                    if last_sig is not None and float((np.abs(sig - last_sig) > _MOTION_PIXEL_DELTA).mean()) < limits.motion_threshold:
                        continue
                    last_sig = sig
                kept += 1
                yield t, frame
        finally:
            cap.release()
    finally:
        os.remove(path)


def analyze_clip(
    data: bytes,
    suffix: str,
    limits: ClipLimits,
    recognize: Callable[[bytes], Dict],
    iou_threshold: float,
    max_gap_s: float,
) -> Dict:
    """Chạy `recognize` (thường là `run_anpr`) trên frame đã cắt rồi gộp thành sự kiện."""
    reads: List[PlateRead] = []
    sampled = 0
    # closing(): recognize ném lỗi giữa chừng vẫn đóng generator ngay → file tạm bị xoá.
    with closing(iter_clip_frames(data, suffix, limits)) as frames:
        for t, frame in frames:
            sampled += 1
            ok, buf = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            result = recognize(buf.tobytes())
            if result["plate_number"] == FALLBACK_PLATE_NUMBER or not result["confidence"]:
                continue
            bbox = result.get("plate_bbox")
            reads.append(PlateRead(t, result["plate_number"], float(result["confidence"]),
                                   tuple(bbox) if bbox else None, result["crop_bytes"]))
    events = [e.summary() for e in group_reads(reads, iou_threshold, max_gap_s)]
    return {"sampled_frames": sampled, "plate_reads": len(reads), "events": events}
