"""Small auditable ridge-regression candidate for occupancy forecasting."""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Any, Iterable, Sequence

import numpy as np


def fit_ridge_models(
    rows: Iterable[dict[str, Any]],
    *,
    feature_columns: Sequence[str],
    alpha: float = 1.0,
    min_rows_per_horizon: int = 20,
) -> dict[str, dict[str, Any]]:
    if alpha < 0:
        raise ValueError("alpha must be non-negative")
    if min_rows_per_horizon <= 0:
        raise ValueError("min_rows_per_horizon must be positive")

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["horizon_slots"])].append(dict(row))

    models: dict[str, dict[str, Any]] = {}
    for horizon, horizon_rows in sorted(grouped.items()):
        if len(horizon_rows) < min_rows_per_horizon:
            continue
        lots = sorted({str(row["parking_lot_id"]) for row in horizon_rows})
        means: dict[str, float] = {}
        scales: dict[str, float] = {}
        for column in feature_columns:
            values = [
                float(row[column])
                for row in horizon_rows
                if row.get(column) is not None
            ]
            means[column] = sum(values) / len(values) if values else 0.0
            variance = (
                sum((value - means[column]) ** 2 for value in values) / len(values)
                if values
                else 0.0
            )
            scales[column] = sqrt(variance) if variance > 1e-12 else 1.0

        model = {
            "horizon_slots": horizon,
            "feature_columns": list(feature_columns),
            "means": means,
            "scales": scales,
            "lot_ids": lots,
            "alpha": alpha,
            "train_rows": len(horizon_rows),
        }
        matrix = np.asarray([_vector(row, model) for row in horizon_rows], dtype=float)
        target = np.asarray(
            [float(row["target_occupancy"]) for row in horizon_rows], dtype=float
        )
        penalty = np.eye(matrix.shape[1], dtype=float) * alpha
        penalty[0, 0] = 0.0
        lhs = matrix.T @ matrix + penalty
        rhs = matrix.T @ target
        try:
            weights = np.linalg.solve(lhs, rhs)
        except np.linalg.LinAlgError:
            weights = np.linalg.pinv(lhs) @ rhs
        model["weights"] = weights.tolist()
        models[str(horizon)] = model
    return models


def _vector(row: dict[str, Any], model: dict[str, Any]) -> list[float]:
    vector = [1.0]
    for column in model["feature_columns"]:
        value = row.get(column)
        if value is None:
            vector.append(0.0)
        else:
            vector.append(
                (float(value) - float(model["means"][column]))
                / float(model["scales"][column])
            )
    for column in model["feature_columns"]:
        vector.append(1.0 if row.get(column) is None else 0.0)
    lot_id = str(row["parking_lot_id"])
    vector.extend(1.0 if lot_id == known else 0.0 for known in model["lot_ids"])
    return vector


def predict(row: dict[str, Any], model: dict[str, Any]) -> float:
    raw = float(np.dot(np.asarray(_vector(row, model)), np.asarray(model["weights"])))
    return min(1.0, max(0.0, raw))


def evaluate_models(
    models: dict[str, dict[str, Any]], rows: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    errors: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        horizon = int(row["horizon_slots"])
        model = models.get(str(horizon))
        if model is None:
            continue
        actual = float(row["target_occupancy"])
        lot_id = str(row["parking_lot_id"])
        predictions = {
            "ridge": predict(row, model),
            "persistence": float(row["last_occupancy"]),
        }
        if row.get("lag_336") is not None:
            predictions["seasonal_naive"] = float(row["lag_336"])
        for name, predicted in predictions.items():
            error = predicted - actual
            errors[(name, horizon, lot_id)].append(error)
            errors[(name, horizon, "__all__")].append(error)

    summary: list[dict[str, Any]] = []
    for (name, horizon, lot_id), values in sorted(errors.items()):
        summary.append(
            {
                "model": name,
                "horizon_slots": horizon,
                "parking_lot_id": lot_id,
                "count": len(values),
                "mae": sum(abs(value) for value in values) / len(values),
                "rmse": sqrt(sum(value * value for value in values) / len(values)),
            }
        )
    return summary


def beats_persistence_every_horizon(
    summary: Sequence[dict[str, Any]],
    *,
    required_horizons: Sequence[int] | None = None,
) -> bool:
    overall = {
        (str(row["model"]), int(row["horizon_slots"])): float(row["mae"])
        for row in summary
        if row["parking_lot_id"] == "__all__"
    }
    horizons = (
        sorted({int(value) for value in required_horizons})
        if required_horizons is not None
        else sorted(horizon for model, horizon in overall if model == "ridge")
    )
    return bool(horizons) and all(
        overall.get(("ridge", horizon), float("inf"))
        < overall.get(("persistence", horizon), float("inf"))
        for horizon in horizons
    )
