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
    beats_baselines_every_horizon,
    evaluate_models,
    fit_ridge_models,
    predict,
)
from training.forecast.run_experiment import (
    ForecastReadinessError,
    run_forecast_experiment,
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
    def test_experiment_stops_before_artifacts_when_readiness_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lake = Path(temporary)

            with self.assertRaises(ForecastReadinessError):
                run_forecast_experiment(
                    data_lake=lake,
                    as_of=datetime(2026, 9, 25, tzinfo=timezone.utc),
                )

            self.assertFalse((lake / "curated").exists())
            self.assertFalse((lake / "models").exists())

    def test_experiment_writes_linked_offline_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lake = Path(temporary)
            partition = lake / "raw" / "parking_sessions" / "export_date=2026-01-06"
            partition.mkdir(parents=True)
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            end = start.replace(day=6)
            row = {
                "session_id": "session-a",
                "parking_lot_id": "lot-a",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "capacity_at_export": 10,
                "updated_at": end.isoformat(),
            }
            data_file = partition / "run.jsonl"
            data_file.write_text(json.dumps(row) + "\n", encoding="utf-8")
            manifest = {
                "data_file": data_file.relative_to(lake).as_posix(),
                "sha256": hashlib.sha256(data_file.read_bytes()).hexdigest(),
                "record_count": 1,
            }
            (partition / "run.manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            state = lake / "_state" / "parking_sessions.json"
            state.parent.mkdir()
            state.write_text(
                json.dumps({"watermark": end.isoformat()}), encoding="utf-8"
            )

            run_path, report = run_forecast_experiment(
                data_lake=lake,
                as_of=end,
                history_days=5,
                minimum_history_days=1,
                horizons=(1, 2),
                lag_slots=(1, 2),
                rolling_windows=(4,),
                minimum_train_rows_per_horizon=10,
            )

            self.assertTrue(run_path.is_file())
            self.assertTrue(Path(report["snapshot_manifest"]).is_file())
            self.assertTrue(Path(report["feature_manifest"]).is_file())
            self.assertTrue(Path(report["candidate_manifest"]).is_file())
            candidate = json.loads(
                Path(report["candidate_manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(
                report["identity"]["candidate_id"], candidate["candidate_id"]
            )
            self.assertEqual(report["promotion"].split(";")[0], "never automatic")

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
            beats_baselines_every_horizon(
                validation,
                required_horizons=(1, 2),
            )
        )
        self.assertFalse(
            beats_baselines_every_horizon(
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

    def test_calendar_features_use_vietnam_local_time_and_holidays(self) -> None:
        # 2026-01-04 17:00 UTC = 00:00 thứ Hai 05/01 giờ VN. Tính theo UTC sẽ ra
        # 17:00 Chủ nhật (cuối tuần).
        monday_local_midnight = int(datetime(2026, 1, 4, 17, 0, tzinfo=timezone.utc).timestamp())
        origin = monday_local_midnight - SLOT
        rows = regularize_history(
            [
                {**_row(0, 0.1), "timestamp": origin},
                {**_row(0, 0.2), "timestamp": monday_local_midnight},
            ]
        )
        [feature] = build_feature_rows(rows, horizons=(1,), lag_slots=(1,), rolling_windows=(1,))

        self.assertEqual(feature["target_is_weekend"], 0.0)
        self.assertAlmostEqual(feature["target_hour_sin"], 0.0, places=9)
        self.assertAlmostEqual(feature["target_hour_cos"], 1.0, places=9)
        self.assertEqual(feature["target_is_holiday"], 0.0)

        tet_noon = int(datetime(2026, 2, 17, 5, 0, tzinfo=timezone.utc).timestamp())
        rows = regularize_history(
            [
                {**_row(0, 0.1), "timestamp": tet_noon - SLOT},
                {**_row(0, 0.2), "timestamp": tet_noon},
            ]
        )
        [feature] = build_feature_rows(rows, horizons=(1,), lag_slots=(1,), rolling_windows=(1,))
        self.assertEqual(feature["target_is_holiday"], 1.0)

    def test_holiday_is_unknown_outside_the_lunar_table(self) -> None:
        [feature] = build_feature_rows(
            regularize_history([_row(0, 0.1), _row(1, 0.2)]),
            horizons=(1,),
            lag_slots=(1,),
            rolling_windows=(1,),
        )
        self.assertIsNone(feature["target_is_holiday"])

    def test_same_slot_features_align_to_target_not_origin(self) -> None:
        rows = regularize_history([_row(slot, slot / 100) for slot in range(12)])
        features = build_feature_rows(
            rows,
            horizons=(2, 5),
            lag_slots=(1,),
            rolling_windows=(1,),
            seasonal_slots=(4,),
        )
        by_key = {(row["origin_timestamp"] // SLOT, row["horizon_slots"]): row for row in features}

        # Gốc ô 6, đích ô 8 → "cùng khung 4 ô trước đích" là ô 4.
        self.assertEqual(by_key[(6, 2)]["target_same_slot_4"], 0.04)
        # Đích ô 11 → ô 7 nằm SAU gốc ô 6: chưa biết lúc dự báo, phải là None.
        self.assertIsNone(by_key[(6, 5)]["target_same_slot_4"])

    def test_seasonal_baseline_uses_target_week_and_gate_needs_best_baseline(self) -> None:
        model = {
            "horizon_slots": 2,
            "feature_columns": [],
            "means": {},
            "scales": {},
            "lot_ids": ["lot-a"],
            "alpha": 1.0,
            "train_rows": 100,
            "weights": [0.5, 0.0],
        }
        row = {
            "parking_lot_id": "lot-a",
            "horizon_slots": 2,
            "target_occupancy": 0.9,
            "last_occupancy": 0.1,
            "lag_336": 0.1,
            "target_same_slot_336": 0.9,
        }
        summary = evaluate_models({"2": model}, [row])
        mae = {
            item["model"]: item["mae"]
            for item in summary
            if item["parking_lot_id"] == "__all__"
        }

        self.assertAlmostEqual(mae["seasonal_naive"], 0.0)
        self.assertAlmostEqual(mae["persistence"], 0.8)
        self.assertAlmostEqual(mae["ridge"], 0.4)
        # Thắng persistence nhưng thua seasonal-naive → không qua cổng.
        self.assertFalse(beats_baselines_every_horizon(summary, required_horizons=(2,)))


if __name__ == "__main__":
    unittest.main()
