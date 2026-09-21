from __future__ import annotations

import unittest
from datetime import datetime, timezone
import hashlib
import json
import tempfile
from pathlib import Path

from training.forecast.baselines import backtest_baselines
from training.forecast.build_features import load_feature_dataset, write_feature_dataset
from training.forecast.dataset import regularize_history
from training.forecast.features import build_feature_rows, temporal_split
from training.forecast.snapshot import load_snapshot, write_snapshot
from training.forecast.ridge_model import (
    beats_persistence_every_horizon,
    evaluate_models,
    fit_ridge_models,
    predict,
)
from training.forecast.train import write_candidate


SLOT = 30 * 60


def _row(slot: int, occupancy: float, lot_id: str = "lot-a") -> dict:
    return {
        "parking_lot_id": lot_id,
        "timestamp": slot * SLOT,
        "avg_occupancy": occupancy,
        "data_quality": "observed",
    }


class ForecastDatasetTest(unittest.TestCase):
    def test_regularize_history_marks_missing_slots_without_zero_imputation(self) -> None:
        rows = [_row(0, 0.25), _row(2, 0.75)]

        result = regularize_history(rows)

        self.assertEqual(len(result), 3)
        self.assertTrue(result[1]["is_missing"])
        self.assertIsNone(result[1]["target_occupancy"])
        self.assertEqual(result[1]["data_quality"], "missing")

    def test_regularize_history_rejects_duplicates(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate history slot"):
            regularize_history([_row(0, 0.25), _row(0, 0.75)])

    def test_backtest_excludes_missing_targets_and_uses_only_past_sources(self) -> None:
        regularized = regularize_history(
            [_row(0, 0.1), _row(1, 0.2), _row(3, 0.4), _row(4, 0.5)]
        )

        result = backtest_baselines(
            regularized,
            horizons=(1,),
            seasonal_period_slots=2,
        )

        self.assertTrue(result["predictions"])
        self.assertTrue(
            all(
                item["source_timestamp"] <= item["origin_timestamp"]
                for item in result["predictions"]
            )
        )
        self.assertTrue(
            all(
                item["target_timestamp"] != 2 * SLOT
                for item in result["predictions"]
            )
        )

    def test_backtest_metrics_are_deterministic(self) -> None:
        regularized = regularize_history(
            [_row(0, 0.1), _row(1, 0.2), _row(2, 0.3), _row(3, 0.4)]
        )

        result = backtest_baselines(
            regularized,
            horizons=(1,),
            seasonal_period_slots=2,
        )
        persistence = next(
            row for row in result["summary"] if row["model"] == "persistence"
        )

        self.assertEqual(persistence["count"], 3)
        self.assertAlmostEqual(persistence["mae"], 0.1)
        self.assertAlmostEqual(persistence["rmse"], 0.1)

    def test_feature_builder_never_reads_after_forecast_origin(self) -> None:
        regularized = regularize_history(
            [_row(slot, slot / 20) for slot in range(10)]
        )

        features = build_feature_rows(
            regularized,
            horizons=(1, 2),
            lag_slots=(1, 2),
            rolling_windows=(4,),
        )

        self.assertTrue(features)
        for row in features:
            self.assertLessEqual(
                row["last_observed_timestamp"], row["origin_timestamp"]
            )
            self.assertGreater(row["target_timestamp"], row["origin_timestamp"])

    def test_feature_builder_preserves_missing_lag_and_missing_fraction(self) -> None:
        regularized = regularize_history(
            [_row(0, 0.1), _row(2, 0.3), _row(3, 0.4)]
        )

        features = build_feature_rows(
            regularized,
            horizons=(1,),
            lag_slots=(1,),
            rolling_windows=(2,),
        )
        row = next(item for item in features if item["origin_timestamp"] == 2 * SLOT)

        self.assertIsNone(row["lag_1"])
        self.assertEqual(row["rolling_missing_fraction_2"], 0.5)

    def test_temporal_split_purges_targets_crossing_boundaries(self) -> None:
        regularized = regularize_history(
            [_row(slot, slot / 30) for slot in range(20)]
        )
        features = build_feature_rows(
            regularized,
            horizons=(1, 4),
            lag_slots=(1,),
            rolling_windows=(2,),
        )

        split = temporal_split(features, validation_fraction=0.2, test_fraction=0.2)

        validation_start = min(row["origin_timestamp"] for row in split["validation"])
        test_start = min(row["origin_timestamp"] for row in split["test"])
        self.assertTrue(
            all(row["target_timestamp"] < validation_start for row in split["train"])
        )
        self.assertTrue(
            all(row["target_timestamp"] < test_start for row in split["validation"])
        )
        self.assertTrue(split["purged"])

    def test_snapshot_is_immutable_and_records_missing_semantics(self) -> None:
        regularized = regularize_history([_row(0, 0.1), _row(2, 0.3)])
        as_of = datetime(2026, 9, 21, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)

            data_file, manifest_file, manifest = write_snapshot(
                regularized,
                output_dir=output,
                source_manifests=[],
                as_of=as_of,
                history_days=30,
            )
            second_data, second_manifest, _ = write_snapshot(
                regularized,
                output_dir=output,
                source_manifests=[],
                as_of=as_of,
                history_days=30,
            )

            self.assertEqual(data_file, second_data)
            self.assertEqual(manifest_file, second_manifest)
            self.assertEqual(manifest["row_count"], 3)
            self.assertEqual(manifest["missing_count"], 1)
            self.assertIn("never interpreted as zero", manifest["missing_semantics"])
            self.assertEqual(
                hashlib.sha256(data_file.read_bytes()).hexdigest(), manifest["sha256"]
            )
            stored_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            self.assertEqual(stored_manifest["snapshot_id"], manifest["snapshot_id"])

            loaded_manifest, loaded_rows = load_snapshot(manifest_file)
            self.assertEqual(loaded_manifest["snapshot_id"], manifest["snapshot_id"])
            self.assertEqual(loaded_rows, regularized)

    def test_feature_artifact_records_split_lineage_and_is_idempotent(self) -> None:
        regularized = regularize_history(
            [_row(slot, slot / 30) for slot in range(20)]
        )
        features = build_feature_rows(
            regularized,
            horizons=(1, 4),
            lag_slots=(1,),
            rolling_windows=(2,),
        )
        split = temporal_split(features)
        source = {"snapshot_id": "occupancy-v1-fixture"}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)

            manifest_path, manifest = write_feature_dataset(
                split,
                output_dir=output,
                source_snapshot=source,
                horizons=(1, 4),
                lag_slots=(1,),
                rolling_windows=(2,),
                validation_fraction=0.2,
                test_fraction=0.2,
            )
            second_path, second_manifest = write_feature_dataset(
                split,
                output_dir=output,
                source_snapshot=source,
                horizons=(1, 4),
                lag_slots=(1,),
                rolling_windows=(2,),
                validation_fraction=0.2,
                test_fraction=0.2,
            )

            self.assertEqual(manifest_path, second_path)
            self.assertEqual(manifest["artifact_id"], second_manifest["artifact_id"])
            self.assertEqual(manifest["source_snapshot_id"], source["snapshot_id"])
            self.assertGreater(manifest["split_counts"]["train"], 0)
            self.assertGreater(manifest["split_counts"]["validation"], 0)
            self.assertGreater(manifest["split_counts"]["test"], 0)

            loaded_manifest, loaded_split = load_feature_dataset(manifest_path)
            self.assertEqual(loaded_manifest["artifact_id"], manifest["artifact_id"])
            self.assertEqual(len(loaded_split["train"]), len(split["train"]))

    def test_ridge_candidate_fits_train_only_and_beats_persistence_on_trend(self) -> None:
        regularized = regularize_history(
            [_row(slot, slot / 200) for slot in range(120)]
        )
        features = build_feature_rows(
            regularized,
            horizons=(1, 2),
            lag_slots=(1, 2),
            rolling_windows=(4,),
        )
        split = temporal_split(features)
        feature_columns = sorted(
            key
            for key in features[0]
            if key
            not in {
                "parking_lot_id",
                "origin_timestamp",
                "target_timestamp",
                "horizon_slots",
                "target_occupancy",
                "last_observed_timestamp",
            }
        )

        models = fit_ridge_models(
            split["train"],
            feature_columns=feature_columns,
            alpha=0.001,
            min_rows_per_horizon=20,
        )
        validation = evaluate_models(models, split["validation"])

        self.assertEqual(set(models), {"1", "2"})
        self.assertTrue(
            beats_persistence_every_horizon(
                validation,
                required_horizons=(1, 2),
            )
        )
        self.assertFalse(
            beats_persistence_every_horizon(
                validation,
                required_horizons=(1, 2, 4),
            )
        )
        example = split["test"][0]
        prediction = predict(example, models[str(example["horizon_slots"])])
        self.assertGreaterEqual(prediction, 0.0)
        self.assertLessEqual(prediction, 1.0)

    def test_candidate_artifact_never_auto_promotes(self) -> None:
        models = {
            "1": {
                "horizon_slots": 1,
                "feature_columns": ["last_occupancy"],
                "means": {"last_occupancy": 0.5},
                "scales": {"last_occupancy": 1.0},
                "lot_ids": ["lot-a"],
                "alpha": 1.0,
                "train_rows": 100,
                "weights": [0.5, 0.0, 0.0, 0.0],
            }
        }
        validation = [
            {
                "model": "ridge",
                "horizon_slots": 1,
                "parking_lot_id": "__all__",
                "count": 10,
                "mae": 0.05,
                "rmse": 0.06,
            },
            {
                "model": "persistence",
                "horizon_slots": 1,
                "parking_lot_id": "__all__",
                "count": 10,
                "mae": 0.1,
                "rmse": 0.12,
            },
        ]
        feature_manifest = {
            "artifact_id": "features-fixture",
            "source_snapshot_id": "snapshot-fixture",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path, candidate = write_candidate(
                output_dir=Path(temporary),
                feature_manifest=feature_manifest,
                models=models,
                validation_metrics=validation,
                test_metrics=validation,
                alpha=1.0,
            )

            self.assertTrue(path.is_file())
            self.assertEqual(
                candidate["status"], "candidate_passed_validation_baseline"
            )
            self.assertIn("never automatic", candidate["promotion"])


if __name__ == "__main__":
    unittest.main()
