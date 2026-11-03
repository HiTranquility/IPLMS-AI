"""Run the reproducible offline Forecast pipeline behind a strict data gate.

This module only creates offline artifacts. It never changes the accepted model
alias and never enables the Forecast runtime endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.infra.datalake import OccupancyReader
from training.forecast.baselines import backtest_baselines
from training.forecast.build_features import write_feature_dataset
from training.forecast.dataset import regularize_history
from training.forecast.features import build_feature_rows, temporal_split
from training.forecast.ridge_model import evaluate_models, fit_ridge_models
from training.forecast.snapshot import source_manifests, write_immutable, write_snapshot
from training.forecast.train import write_candidate
from training.readiness import inspect_forecast


class ForecastReadinessError(RuntimeError):
    """Raised before artifact creation when the raw-data contract is not ready."""

    def __init__(self, report: dict[str, Any]) -> None:
        super().__init__("forecast data did not pass the readiness gate")
        self.report = report


def summarize_readiness(report: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, log-safe view without hundreds of per-lot entries."""

    histories = list((report.get("lot_history") or {}).values())
    longest_history_days = max(
        (float(item.get("history_days") or 0.0) for item in histories),
        default=0.0,
    )
    return {
        "ready": bool(report.get("ready")),
        "data_lake": report.get("data_lake"),
        "minimum_history_days": report.get("minimum_history_days"),
        "data_files": report.get("data_files"),
        "record_count": report.get("record_count"),
        "parking_lot_count": len(histories),
        "eligible_lot_count": len(report.get("eligible_lots") or []),
        "longest_history_days": longest_history_days,
        "watermark_present": bool(report.get("watermark_present")),
        "errors": report.get("errors") or [],
        "warnings": report.get("warnings") or [],
    }


def _parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("--as-of must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _positive_csv(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not parsed or any(item <= 0 for item in parsed):
        raise argparse.ArgumentTypeError("all values must be positive")
    return parsed


def run_forecast_experiment(
    *,
    data_lake: Path,
    as_of: datetime,
    history_days: int = 365,
    minimum_history_days: int = 30,
    horizons: Sequence[int] = (1, 2, 4, 8),
    lag_slots: Sequence[int] = (1, 2, 48, 336),
    rolling_windows: Sequence[int] = (4, 48),
    validation_fraction: float = 0.2,
    test_fraction: float = 0.2,
    alpha: float = 1.0,
    minimum_train_rows_per_horizon: int = 100,
) -> tuple[Path, dict[str, Any]]:
    """Create snapshot, baseline, features and a candidate from verified raw data."""

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if history_days <= 0 or minimum_history_days <= 0:
        raise ValueError("history day limits must be positive")

    readiness = inspect_forecast(
        data_lake,
        min_history_days=minimum_history_days,
    )
    if not readiness["ready"]:
        raise ForecastReadinessError(readiness)

    lot_ids = list(readiness["eligible_lots"])
    reader = OccupancyReader(base_path=data_lake)
    observed: list[dict[str, Any]] = []
    for lot_id in lot_ids:
        observed.extend(
            reader.load_historical_occupancy(
                lot_id,
                days=history_days,
                now=as_of,
            )
        )
    if not observed:
        raise ValueError("eligible raw sessions produced no occupancy observations")

    regularized = regularize_history(observed)
    _snapshot_data, snapshot_manifest_path, snapshot = write_snapshot(
        regularized,
        output_dir=data_lake / "curated" / "occupancy",
        source_manifests=source_manifests(data_lake),
        as_of=as_of,
        history_days=history_days,
    )

    baseline = backtest_baselines(
        regularized,
        horizons=horizons,
        seasonal_period_slots=7 * 24 * 2,
    )
    if not baseline["summary"]:
        raise ValueError("snapshot produced no evaluable baseline observations")

    feature_rows = build_feature_rows(
        regularized,
        horizons=horizons,
        lag_slots=lag_slots,
        rolling_windows=rolling_windows,
    )
    if not feature_rows:
        raise ValueError("snapshot produced no supervised feature rows")
    split = temporal_split(
        feature_rows,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
    )
    feature_manifest_path, feature_manifest = write_feature_dataset(
        split,
        output_dir=data_lake / "curated" / "forecast_features",
        source_snapshot=snapshot,
        horizons=horizons,
        lag_slots=lag_slots,
        rolling_windows=rolling_windows,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
    )

    models = fit_ridge_models(
        split["train"],
        feature_columns=feature_manifest["feature_columns"],
        alpha=alpha,
        min_rows_per_horizon=minimum_train_rows_per_horizon,
    )
    if not models:
        raise ValueError("no horizon has enough training rows")
    validation_metrics = evaluate_models(models, split["validation"])
    test_metrics = evaluate_models(models, split["test"])
    if not validation_metrics or not test_metrics:
        raise ValueError("validation/test split has no rows for fitted horizons")
    candidate_path, candidate = write_candidate(
        output_dir=data_lake / "models" / "forecast-candidates",
        feature_manifest=feature_manifest,
        models=models,
        validation_metrics=validation_metrics,
        test_metrics=test_metrics,
        alpha=alpha,
    )

    identity = {
        "snapshot_id": snapshot["snapshot_id"],
        "feature_artifact_id": feature_manifest["artifact_id"],
        "candidate_id": candidate["candidate_id"],
        "horizons": list(horizons),
    }
    identity_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    run_id = f"forecast-run-{identity_hash[:16]}"
    run_path = data_lake / "reports" / "forecast-runs" / f"{run_id}.json"
    if run_path.exists():
        stored = json.loads(run_path.read_text(encoding="utf-8"))
        if stored.get("identity") != identity:
            raise FileExistsError(f"immutable experiment conflict: {run_path}")
        return run_path, stored

    run_path.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": candidate["status"],
        "identity": identity,
        "as_of": as_of.astimezone(timezone.utc).isoformat(),
        "history_days": history_days,
        "minimum_history_days": minimum_history_days,
        "eligible_lots": lot_ids,
        "readiness": readiness,
        "snapshot_manifest": str(snapshot_manifest_path.resolve()),
        "feature_manifest": str(feature_manifest_path.resolve()),
        "candidate_manifest": str(candidate_path.resolve()),
        "baseline_summary": baseline["summary"],
        "baseline_prediction_count": len(baseline["predictions"]),
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "promotion": "never automatic; review this report and shadow-test separately",
    }
    write_immutable(
        run_path,
        (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    return run_path, report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the gated, reproducible offline Forecast experiment."
    )
    parser.add_argument("--data-lake", type=Path, default=Path("data/datalake"))
    parser.add_argument("--as-of", type=_parse_instant, required=True)
    parser.add_argument("--history-days", type=int, default=365)
    parser.add_argument("--minimum-history-days", type=int, default=30)
    parser.add_argument("--horizons", type=_positive_csv, default=(1, 2, 4, 8))
    parser.add_argument("--lags", type=_positive_csv, default=(1, 2, 48, 336))
    parser.add_argument("--rolling-windows", type=_positive_csv, default=(4, 48))
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--minimum-train-rows-per-horizon", type=int, default=100)
    args = parser.parse_args()

    try:
        path, report = run_forecast_experiment(
            data_lake=args.data_lake,
            as_of=args.as_of,
            history_days=args.history_days,
            minimum_history_days=args.minimum_history_days,
            horizons=args.horizons,
            lag_slots=args.lags,
            rolling_windows=args.rolling_windows,
            validation_fraction=args.validation_fraction,
            test_fraction=args.test_fraction,
            alpha=args.alpha,
            minimum_train_rows_per_horizon=args.minimum_train_rows_per_horizon,
        )
    except ForecastReadinessError as exc:
        print(
            json.dumps(
                {
                    "status": "blocked_readiness",
                    "reason": str(exc),
                    "readiness": summarize_readiness(exc.report),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    except (FileExistsError, ValueError) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "run_id": report["run_id"],
                "status": report["status"],
                "report": str(path.resolve()),
                "candidate_manifest": report["candidate_manifest"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["status"] == "candidate_passed_validation_baseline" else 1


if __name__ == "__main__":
    raise SystemExit(main())
