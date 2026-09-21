"""Leakage-safe baseline evaluation for occupancy forecasts."""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Any, Iterable, Sequence


def _is_observed(row: dict[str, Any]) -> bool:
    return not bool(row.get("is_missing")) and row.get("target_occupancy") is not None


def _summary(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for item in predictions:
        key = (
            str(item["model"]),
            str(item["parking_lot_id"]),
            int(item["horizon_slots"]),
        )
        buckets[key].append(item)

    output: list[dict[str, Any]] = []
    for (model, lot_id, horizon), values in sorted(buckets.items()):
        count = len(values)
        output.append(
            {
                "model": model,
                "parking_lot_id": lot_id,
                "horizon_slots": horizon,
                "count": count,
                "mae": sum(item["abs_error"] for item in values) / count,
                "rmse": sqrt(sum(item["squared_error"] for item in values) / count),
            }
        )
    return output


def backtest_baselines(
    rows: Iterable[dict[str, Any]],
    *,
    horizons: Sequence[int] = (1, 2, 4, 8),
    seasonal_period_slots: int = 7 * 24 * 2,
) -> dict[str, list[dict[str, Any]]]:
    """Evaluate persistence and seasonal-naive baselines.

    ``rows`` must already be regularized and sorted into fixed slots. A forecast
    made at an origin can only use observations at or before that origin. Missing
    targets are excluded from metrics; they are not imputed as zero.
    """

    normalized_horizons = sorted({int(value) for value in horizons})
    if not normalized_horizons or normalized_horizons[0] <= 0:
        raise ValueError("horizons must contain positive integers")
    if seasonal_period_slots <= 0:
        raise ValueError("seasonal_period_slots must be positive")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["parking_lot_id"])].append(dict(row))

    predictions: list[dict[str, Any]] = []
    for lot_id, series in sorted(grouped.items()):
        series.sort(key=lambda item: int(item["timestamp"]))
        latest_observed_index: list[int | None] = []
        latest: int | None = None
        for index, row in enumerate(series):
            if _is_observed(row):
                latest = index
            latest_observed_index.append(latest)

        for origin_index, origin in enumerate(series):
            source_index = latest_observed_index[origin_index]
            for horizon in normalized_horizons:
                target_index = origin_index + horizon
                if target_index >= len(series):
                    continue
                target = series[target_index]
                if not _is_observed(target):
                    continue
                actual = float(target["target_occupancy"])

                if source_index is not None:
                    source = series[source_index]
                    predicted = float(source["target_occupancy"])
                    predictions.append(
                        _prediction(
                            model="persistence",
                            lot_id=lot_id,
                            horizon=horizon,
                            origin=origin,
                            target=target,
                            source=source,
                            predicted=predicted,
                            actual=actual,
                        )
                    )

                seasonal_index = target_index - seasonal_period_slots
                if seasonal_index < 0 or seasonal_index > origin_index:
                    continue
                seasonal_source = series[seasonal_index]
                if not _is_observed(seasonal_source):
                    continue
                predicted = float(seasonal_source["target_occupancy"])
                predictions.append(
                    _prediction(
                        model="seasonal_naive",
                        lot_id=lot_id,
                        horizon=horizon,
                        origin=origin,
                        target=target,
                        source=seasonal_source,
                        predicted=predicted,
                        actual=actual,
                    )
                )

    return {"predictions": predictions, "summary": _summary(predictions)}


def _prediction(
    *,
    model: str,
    lot_id: str,
    horizon: int,
    origin: dict[str, Any],
    target: dict[str, Any],
    source: dict[str, Any],
    predicted: float,
    actual: float,
) -> dict[str, Any]:
    error = predicted - actual
    return {
        "model": model,
        "parking_lot_id": lot_id,
        "horizon_slots": horizon,
        "origin_timestamp": int(origin["timestamp"]),
        "target_timestamp": int(target["timestamp"]),
        "source_timestamp": int(source["timestamp"]),
        "predicted": predicted,
        "actual": actual,
        "abs_error": abs(error),
        "squared_error": error * error,
    }
