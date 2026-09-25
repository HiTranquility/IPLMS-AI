"""Pure request-measurement helpers shared by benchmark CLIs and tests."""

from __future__ import annotations

import re
from collections import Counter
from math import ceil
from statistics import mean
from typing import Any, Iterable


def normalize_plate(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")
    index = max(0, ceil(len(ordered) * quantile) - 1)
    return ordered[index]


def distribution(values: Iterable[float]) -> dict[str, float | int | None]:
    samples = [float(value) for value in values]
    if not samples:
        return {
            "count": 0,
            "min": None,
            "mean": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    return {
        "count": len(samples),
        "min": min(samples),
        "mean": mean(samples),
        "p50": percentile(samples, 0.50),
        "p95": percentile(samples, 0.95),
        "p99": percentile(samples, 0.99),
        "max": max(samples),
    }


def summarize_requests(
    samples: Iterable[dict[str, Any]],
    *,
    wall_time_seconds: float,
    expected_plate: str | None = None,
) -> dict[str, Any]:
    rows = list(samples)
    successful = [row for row in rows if row.get("ok")]
    failed = [row for row in rows if not row.get("ok")]
    expected_normalized = normalize_plate(expected_plate)
    strict_matches = 0
    normalized_matches = 0
    if expected_plate is not None:
        strict_expected = expected_plate.strip().upper()
        strict_matches = sum(
            str(row.get("plate_number") or "").strip().upper() == strict_expected
            for row in successful
        )
        normalized_matches = sum(
            normalize_plate(str(row.get("plate_number") or "")) == expected_normalized
            for row in successful
        )

    attempted = len(rows)
    return {
        "attempted": attempted,
        "successful": len(successful),
        "failed": len(failed),
        "error_rate": len(failed) / attempted if attempted else 0.0,
        "wall_time_seconds": wall_time_seconds,
        "throughput_rps": attempted / wall_time_seconds if wall_time_seconds > 0 else 0.0,
        "rtt_ms": distribution(row["rtt_ms"] for row in successful),
        "server_process_ms": distribution(
            row["server_process_ms"] for row in successful
        ),
        "transport_overhead_ms": distribution(
            row["transport_overhead_ms"] for row in successful
        ),
        "grpc_status_counts": dict(
            sorted(Counter(str(row.get("grpc_status") or "UNKNOWN") for row in rows).items())
        ),
        "plate_counts": dict(
            sorted(Counter(str(row.get("plate_number") or "") for row in successful).items())
        ),
        "confidence": distribution(row["confidence"] for row in successful),
        "expected_plate": expected_plate,
        "strict_match_rate": (
            strict_matches / attempted if expected_plate is not None and attempted else None
        ),
        "normalized_match_rate": (
            normalized_matches / attempted
            if expected_plate is not None and attempted
            else None
        ),
    }


def evaluate_gates(
    summary: dict[str, Any],
    *,
    max_error_rate: float | None = None,
    max_p95_ms: float | None = None,
    min_normalized_match_rate: float | None = None,
) -> list[str]:
    failures: list[str] = []
    if max_error_rate is not None and summary["error_rate"] > max_error_rate:
        failures.append(
            f"error_rate {summary['error_rate']:.4f} > {max_error_rate:.4f}"
        )
    p95 = summary["rtt_ms"]["p95"]
    if max_p95_ms is not None and (p95 is None or p95 > max_p95_ms):
        failures.append(f"rtt p95 {p95} > {max_p95_ms}")
    match_rate = summary.get("normalized_match_rate")
    if min_normalized_match_rate is not None and (
        match_rate is None or match_rate < min_normalized_match_rate
    ):
        failures.append(
            f"normalized_match_rate {match_rate} < {min_normalized_match_rate}"
        )
    return failures
