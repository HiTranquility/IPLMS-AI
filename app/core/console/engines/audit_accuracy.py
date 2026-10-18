"""Độ chính xác THẬT của ANPR trên tập bốc ngẫu nhiên + đề xuất ngưỡng (PROB-049 §6).

Chỉ tính trên mẫu `random_audit` — tập low-confidence cố tình lệch xấu nên không
dùng để báo "AI đúng bao nhiêu %". Ngưỡng chỉ được ĐỀ XUẤT; AI Lead duyệt.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional

from app.core.dataset.engines.plate_metrics import normalize_relaxed

TARGET_ACCURACY = 0.98
MIN_SAMPLES = 20
_THRESHOLDS = [round(0.50 + 0.01 * i, 2) for i in range(50)]  # 0.50 … 0.99


def wilson_interval(correct: int, total: int, z: float = 1.96) -> Optional[tuple[float, float]]:
    """Khoảng tin cậy 95% cho tỉ lệ — mẫu nhỏ thì khoảng rộng, nói thật độ chắc."""
    if total == 0:
        return None
    p = correct / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return round(max(0.0, centre - margin), 4), round(min(1.0, centre + margin), 4)


def is_correct(machine_plate: str, truth: str) -> bool:
    return bool(truth) and normalize_relaxed(machine_plate) == normalize_relaxed(truth)


def accuracy_report(
    samples: Iterable[dict], target: float = TARGET_ACCURACY, min_samples: int = MIN_SAMPLES
) -> dict:
    rows = [(float(s["confidence"]), is_correct(s["machine_plate"], s["truth"])) for s in samples]
    total = len(rows)
    correct = sum(ok for _, ok in rows)

    buckets = []
    for i in range(10):
        lo, hi = i / 10, (i + 1) / 10
        inside = [ok for conf, ok in rows if lo <= conf < hi or (i == 9 and conf == 1.0)]
        buckets.append({
            "from": lo, "to": hi, "total": len(inside), "correct": sum(inside),
            "accuracy": round(sum(inside) / len(inside), 4) if inside else None,
        })

    curve, suggested = [], None
    for t in _THRESHOLDS:
        above = [ok for conf, ok in rows if conf >= t]
        acc = sum(above) / len(above) if above else None
        curve.append({
            "threshold": t, "total": len(above),
            "accuracy": round(acc, 4) if acc is not None else None,
            "coverage": round(len(above) / total, 4) if total else None,
        })
        if suggested is None and len(above) >= min_samples and acc is not None and acc >= target:
            suggested = t

    if total < min_samples:
        reason = f"Cần ít nhất {min_samples} mẫu audit đã có nhãn người; hiện có {total}."
    elif suggested is None:
        reason = f"Không ngưỡng nào đạt {target:.0%} với ≥ {min_samples} mẫu phía trên."
    else:
        reason = (
            f"Ngưỡng thấp nhất mà các mẫu có confidence ≥ ngưỡng đúng ≥ {target:.0%} "
            f"(≥ {min_samples} mẫu)."
        )
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else None,
        "interval_95": wilson_interval(correct, total),
        "target": target,
        "min_samples": min_samples,
        "buckets": buckets,
        "curve": curve,
        "suggested_threshold": suggested,
        "suggestion_reason": reason,
    }
