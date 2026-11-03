"""Đo độ chính xác ANPR trên một snapshot đã khoá (ISSUE-013).

Backend gửi danh sách mẫu test-golden (URL ảnh cắt trong Storage + nhãn người
gán); service này tải từng ảnh, chạy ĐÚNG engine đang phục vụ
(`anpr_engine.run_anpr`) và chấm bằng `plate_metrics` — cùng thước đo với CLI
`training/eval_plates.py`, để số trên UI và số trong PR so được với nhau.
"""
from __future__ import annotations

import hashlib
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from app.config import get_config
from app.core.dataset.engines.plate_metrics import aggregate, score_one

MAX_IMAGE_BYTES = 8 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 15
MAX_FAILURES_REPORTED = 50
CONFIDENCE_BUCKETS = 10


from app.core.dataset.dtos.sample_dto import EvaluationSample


def fetch_image(url: str) -> bytes:
    """Tải ảnh qua http(s). URL do backend dựng từ key Storage, không từ người dùng."""
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL ảnh không hợp lệ: {scheme or 'thiếu scheme'}")
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as resp:  # noqa: S310
        data = resp.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Ảnh quá lớn")
    return data


def _run_engine(image: bytes) -> Dict[str, object]:
    from app.core.vision.engines.anpr.engine import run_anpr

    return run_anpr(image)


def model_version() -> str:
    """Định danh model đang phục vụ: hash weights YOLO + phiên bản EasyOCR."""
    weights = Path(get_config().vision.yolo_model_path)
    digest = "missing"
    if weights.exists():
        digest = hashlib.sha256(weights.read_bytes()).hexdigest()[:12]
    try:
        from importlib.metadata import version

        ocr = version("easyocr")
    except Exception:  # noqa: BLE001 — chỉ là nhãn, thiếu thì ghi unknown
        ocr = "unknown"
    return f"yolo:{digest}+easyocr:{ocr}"


def evaluate_one(
    sample: EvaluationSample,
    *,
    fetch: Callable[[str], bytes] = fetch_image,
    run: Callable[[bytes], Dict[str, object]] = _run_engine,
) -> Dict[str, object]:
    """Một ảnh → một dòng số liệu. Lỗi (tải ảnh, engine) GHI LẠI, không làm hỏng cả lượt."""
    from app.core.constants import FALLBACK_PLATE_NUMBER

    predicted: Optional[str] = None
    confidence: Optional[float] = None
    process_time: Optional[float] = None
    error: Optional[str] = None
    try:
        result = run(fetch(sample.image_url))
        predicted = result.get("plate_number")  # type: ignore[assignment]
        confidence = result.get("confidence")  # type: ignore[assignment]
        process_time = result.get("process_time")  # type: ignore[assignment]
        if predicted == FALLBACK_PLATE_NUMBER:
            predicted = None
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        confidence = 0.0
    return {
        **score_one(sample.label, predicted),
        "sample_id": sample.sample_id,
        "confidence": confidence,
        "process_time": process_time,
        "error": error,
    }


def _histogram(values: Iterable[float]) -> List[int]:
    counts = [0] * CONFIDENCE_BUCKETS
    for value in values:
        idx = min(int(max(value, 0.0) * CONFIDENCE_BUCKETS), CONFIDENCE_BUCKETS - 1)
        counts[idx] += 1
    return counts


def summarize(rows: List[Dict[str, object]]) -> Dict[str, object]:
    """Bảng số của cả lượt + phân bố độ tin cậy đúng/sai (để chỉnh ngưỡng 0.75)."""
    correct = [float(r["confidence"] or 0.0) for r in rows if r["exact_relaxed"]]
    wrong = [float(r["confidence"] or 0.0) for r in rows if not r["exact_relaxed"]]
    failures = [
        {
            "sampleId": r["sample_id"],
            "truth": r["truth"],
            "predicted": r["predicted"],
            "confidence": r["confidence"],
            "cer": r["cer"],
            "error": r["error"],
        }
        for r in rows
        if not r["exact_relaxed"]
    ][:MAX_FAILURES_REPORTED]
    return {
        **aggregate(rows),
        "confidenceBuckets": {"correct": _histogram(correct), "wrong": _histogram(wrong)},
        "failures": failures,
    }
