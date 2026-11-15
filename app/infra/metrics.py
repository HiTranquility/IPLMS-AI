"""Thread-safe Prometheus text exposition metrics for the IPLMS AI service.

Uses standard library synchronization so `/metrics` works in any Python
environment without adding external third-party packages.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Dict, Iterator, List, Tuple

INFERENCE_BUCKETS: Tuple[float, ...] = (
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
)

_lock = threading.Lock()
_bucket_counts: Dict[Tuple[str, str], List[int]] = {}
_inf_counts: Dict[Tuple[str, str], int] = {}
_sums: Dict[Tuple[str, str], float] = {}


def _ensure_key(key: Tuple[str, str]) -> None:
    if key not in _bucket_counts:
        _bucket_counts[key] = [0 for _ in INFERENCE_BUCKETS]
        _inf_counts[key] = 0
        _sums[key] = 0.0


# Pre-seed standard model series so Prometheus always sees valid series at startup
for _model in ("anpr", "forecast", "copilot", "anpr_yolo_ocr", "vehicle_classifier"):
    for _status in ("success", "error"):
        _ensure_key((_model, _status))


def observe_ai_inference(model: str, status: str, duration_seconds: float) -> None:
    """Record a single AI model inference observation in seconds."""
    safe_duration = max(0.0, float(duration_seconds))
    key = (str(model), str(status))
    with _lock:
        _ensure_key(key)
        buckets = _bucket_counts[key]
        for idx, bound in enumerate(INFERENCE_BUCKETS):
            if safe_duration <= bound:
                buckets[idx] += 1
        _inf_counts[key] += 1
        _sums[key] += safe_duration


@contextmanager
def track_ai_inference(model: str) -> Iterator[None]:
    """Context manager measuring model execution duration and status."""
    start = time.perf_counter()
    try:
        yield
        observe_ai_inference(model, "success", time.perf_counter() - start)
    except Exception:
        observe_ai_inference(model, "error", time.perf_counter() - start)
        raise


def render_prometheus_metrics() -> str:
    """Render metrics in Prometheus 0.0.4 text exposition format."""
    lines: List[str] = [
        "# HELP iplms_ai_inference_duration_seconds AI model inference duration in seconds by model and status",
        "# TYPE iplms_ai_inference_duration_seconds histogram",
    ]
    with _lock:
        items = sorted(_bucket_counts.keys())
        for model, status in items:
            buckets = list(_bucket_counts[(model, status)])
            total_count = _inf_counts[(model, status)]
            total_sum = _sums[(model, status)]
            for idx, bound in enumerate(INFERENCE_BUCKETS):
                lines.append(
                    f'iplms_ai_inference_duration_seconds_bucket{{model="{model}",status="{status}",le="{bound}"}} {buckets[idx]}'
                )
            lines.append(
                f'iplms_ai_inference_duration_seconds_bucket{{model="{model}",status="{status}",le="+Inf"}} {total_count}'
            )
            lines.append(
                f'iplms_ai_inference_duration_seconds_sum{{model="{model}",status="{status}"}} {total_sum:.6f}'
            )
            lines.append(
                f'iplms_ai_inference_duration_seconds_count{{model="{model}",status="{status}"}} {total_count}'
            )
    lines.append("")
    return "\n".join(lines)
