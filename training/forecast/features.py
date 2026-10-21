"""Point-in-time-correct features and temporal splits for Forecast training."""

from __future__ import annotations

from collections import defaultdict
from math import cos, pi, sin
from typing import Any, Iterable, Sequence

from training.forecast.calendar_vn import (
    VN_UTC_OFFSET_HOURS,
    is_vn_public_holiday,
    to_local,
)


def _observed(row: dict[str, Any]) -> bool:
    return not bool(row.get("is_missing")) and row.get("target_occupancy") is not None


def _value(series: list[dict[str, Any]], index: int) -> float | None:
    if index < 0 or index >= len(series) or not _observed(series[index]):
        return None
    return float(series[index]["target_occupancy"])


def _rolling(
    series: list[dict[str, Any]], origin_index: int, window: int
) -> tuple[float | None, float]:
    start = max(0, origin_index - window + 1)
    window_rows = series[start : origin_index + 1]
    values = [float(row["target_occupancy"]) for row in window_rows if _observed(row)]
    missing_fraction = 1.0 - (len(values) / len(window_rows))
    mean = sum(values) / len(values) if values else None
    return mean, missing_fraction


def build_feature_rows(
    rows: Iterable[dict[str, Any]],
    *,
    horizons: Sequence[int] = (1, 2, 4, 8),
    lag_slots: Sequence[int] = (1, 2, 48, 336),
    rolling_windows: Sequence[int] = (4, 48),
    seasonal_slots: Sequence[int] = (48, 336),
    utc_offset_hours: float = VN_UTC_OFFSET_HOURS,
) -> list[dict[str, Any]]:
    """Build supervised rows without reading data after the forecast origin.

    Calendar features describe the target timestamp in the lot's local time and
    are therefore known in advance. Occupancy lag and rolling features use only
    indices at or before ``origin_timestamp``. ``target_same_slot_<n>`` is the
    value ``n`` slots before the TARGET (same slot yesterday / last week), kept
    only when that slot is not after the origin. Missing values stay ``None``.
    """

    normalized_horizons = sorted({int(value) for value in horizons})
    normalized_lags = sorted({int(value) for value in lag_slots})
    normalized_windows = sorted({int(value) for value in rolling_windows})
    normalized_seasonal = sorted({int(value) for value in seasonal_slots})
    if not normalized_horizons or any(value <= 0 for value in normalized_horizons):
        raise ValueError("horizons must contain positive integers")
    if any(
        value <= 0
        for value in normalized_lags + normalized_windows + normalized_seasonal
    ):
        raise ValueError("lag slots, rolling windows and seasonal slots must be positive")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["parking_lot_id"])].append(dict(row))

    output: list[dict[str, Any]] = []
    for lot_id, series in sorted(grouped.items()):
        series.sort(key=lambda item: int(item["timestamp"]))
        latest_observed_index: int | None = None
        for origin_index, origin in enumerate(series):
            if _observed(origin):
                latest_observed_index = origin_index
            if latest_observed_index is None:
                continue

            for horizon in normalized_horizons:
                target_index = origin_index + horizon
                if target_index >= len(series) or not _observed(series[target_index]):
                    continue
                target = series[target_index]
                # Giờ/ngày theo giờ VN: tính theo UTC thì "thứ Hai" bắt đầu lúc
                # 07:00 sáng và cờ cuối tuần/ngày lễ lệch 7 tiếng.
                target_time = to_local(int(target["timestamp"]), utc_offset_hours)
                hour_angle = 2 * pi * (target_time.hour + target_time.minute / 60) / 24
                weekday_angle = 2 * pi * target_time.weekday() / 7
                holiday = is_vn_public_holiday(target_time.date())
                feature_row: dict[str, Any] = {
                    "parking_lot_id": lot_id,
                    "origin_timestamp": int(origin["timestamp"]),
                    "target_timestamp": int(target["timestamp"]),
                    "horizon_slots": horizon,
                    "target_occupancy": float(target["target_occupancy"]),
                    "last_occupancy": _value(series, latest_observed_index),
                    "last_observed_timestamp": int(
                        series[latest_observed_index]["timestamp"]
                    ),
                    "target_hour_sin": sin(hour_angle),
                    "target_hour_cos": cos(hour_angle),
                    "target_weekday_sin": sin(weekday_angle),
                    "target_weekday_cos": cos(weekday_angle),
                    "target_is_weekend": 1.0 if target_time.weekday() >= 5 else 0.0,
                    "target_is_holiday": None if holiday is None else float(holiday),
                }
                for period in normalized_seasonal:
                    source_index = target_index - period
                    feature_row[f"target_same_slot_{period}"] = (
                        _value(series, source_index) if source_index <= origin_index else None
                    )
                for lag in normalized_lags:
                    feature_row[f"lag_{lag}"] = _value(series, origin_index - lag)
                for window in normalized_windows:
                    mean, missing_fraction = _rolling(series, origin_index, window)
                    feature_row[f"rolling_mean_{window}"] = mean
                    feature_row[f"rolling_missing_fraction_{window}"] = missing_fraction
                output.append(feature_row)

    return output


def temporal_split(
    rows: Iterable[dict[str, Any]],
    *,
    validation_fraction: float = 0.2,
    test_fraction: float = 0.2,
) -> dict[str, list[dict[str, Any]]]:
    """Split each lot by forecast origin and purge targets across boundaries."""

    if validation_fraction <= 0 or test_fraction <= 0:
        raise ValueError("validation_fraction and test_fraction must be positive")
    if validation_fraction + test_fraction >= 1:
        raise ValueError("validation_fraction + test_fraction must be below 1")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["parking_lot_id"])].append(dict(row))

    split: dict[str, list[dict[str, Any]]] = {
        "train": [],
        "validation": [],
        "test": [],
        "purged": [],
    }
    for lot_id, series in sorted(grouped.items()):
        origins = sorted({int(row["origin_timestamp"]) for row in series})
        if len(origins) < 3:
            raise ValueError(f"parking lot {lot_id} needs at least three forecast origins")
        validation_index = max(1, int(len(origins) * (1 - validation_fraction - test_fraction)))
        test_index = max(validation_index + 1, int(len(origins) * (1 - test_fraction)))
        if test_index >= len(origins):
            test_index = len(origins) - 1
        validation_start = origins[validation_index]
        test_start = origins[test_index]

        for row in series:
            origin = int(row["origin_timestamp"])
            target = int(row["target_timestamp"])
            if origin < validation_start:
                bucket = "train" if target < validation_start else "purged"
            elif origin < test_start:
                bucket = "validation" if target < test_start else "purged"
            else:
                bucket = "test"
            split[bucket].append(row)

    for bucket in split.values():
        bucket.sort(
            key=lambda row: (
                str(row["parking_lot_id"]),
                int(row["origin_timestamp"]),
                int(row["horizon_slots"]),
            )
        )
    return split
