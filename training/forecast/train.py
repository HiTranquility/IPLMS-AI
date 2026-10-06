"""Train an offline ridge candidate; never promotes or serves the model."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from training.forecast.build_features import load_feature_dataset
from training.forecast.ridge_model import (
    beats_baselines_every_horizon,
    evaluate_models,
    fit_ridge_models,
)
from training.forecast.snapshot import write_immutable


def write_candidate(
    *,
    output_dir: Path,
    feature_manifest: dict[str, Any],
    models: dict[str, dict[str, Any]],
    validation_metrics: list[dict[str, Any]],
    test_metrics: list[dict[str, Any]],
    alpha: float,
) -> tuple[Path, dict[str, Any]]:
    passed = beats_baselines_every_horizon(
        validation_metrics,
        required_horizons=[int(value) for value in models],
    )
    identity = {
        "feature_artifact_id": feature_manifest["artifact_id"],
        "models": models,
        "alpha": alpha,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    candidate_id = f"forecast-ridge-{digest[:16]}"
    candidate_dir = output_dir / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = candidate_dir / "candidate.json"
    if manifest_path.exists():
        stored = json.loads(manifest_path.read_text(encoding="utf-8"))
        if stored.get("candidate_id") != candidate_id:
            raise FileExistsError(f"immutable candidate conflict: {manifest_path}")
        return manifest_path, stored

    manifest: dict[str, Any] = {
        "candidate_id": candidate_id,
        "model_family": "ridge_regression_per_horizon",
        "status": (
            "candidate_passed_validation_baseline"
            if passed
            else "candidate_failed_validation_baseline"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_artifact_id": feature_manifest["artifact_id"],
        "source_snapshot_id": feature_manifest["source_snapshot_id"],
        "alpha": alpha,
        "models": models,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "promotion": "never automatic; requires reviewed gates and shadow rollout",
    }
    write_immutable(
        manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    return manifest_path, manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train and evaluate an offline ridge Forecast candidate."
    )
    parser.add_argument("--feature-manifest", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("data/datalake/models/forecast-candidates")
    )
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--min-train-rows-per-horizon", type=int, default=100)
    args = parser.parse_args()

    feature_manifest, split = load_feature_dataset(args.feature_manifest)
    models = fit_ridge_models(
        split["train"],
        feature_columns=feature_manifest["feature_columns"],
        alpha=args.alpha,
        min_rows_per_horizon=args.min_train_rows_per_horizon,
    )
    if not models:
        parser.error("no horizon has enough training rows")
    validation_metrics = evaluate_models(models, split["validation"])
    test_metrics = evaluate_models(models, split["test"])
    if not validation_metrics or not test_metrics:
        parser.error("validation/test split has no rows for the fitted horizons")

    path, candidate = write_candidate(
        output_dir=args.output,
        feature_manifest=feature_manifest,
        models=models,
        validation_metrics=validation_metrics,
        test_metrics=test_metrics,
        alpha=args.alpha,
    )
    print(
        json.dumps(
            {
                "candidate_id": candidate["candidate_id"],
                "status": candidate["status"],
                "manifest": str(path.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if candidate["status"] == "candidate_passed_validation_baseline" else 1


if __name__ == "__main__":
    raise SystemExit(main())
