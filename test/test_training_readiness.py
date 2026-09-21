from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from training.readiness import inspect_forecast, inspect_vision


class TrainingReadinessTest(unittest.TestCase):
    def test_vision_checks_sample_and_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            golden = Path(temporary)
            images = golden / "images"
            images.mkdir()
            image = images / "sample.jpg"
            image.write_bytes(b"image-content")
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            (golden / "manifest.json").write_text(
                json.dumps(
                    {
                        "images_dir": "images",
                        "items": [
                            {
                                "file": image.name,
                                "plate": "51F12345",
                                "sha256": digest,
                                "source": "fixture",
                                "tags": ["night"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = inspect_vision(golden, min_samples=1)

            self.assertTrue(report["ready"])
            self.assertEqual(report["tag_counts"], {"night": 1})

    def test_forecast_requires_manifest_watermark_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lake = Path(temporary)
            partition = lake / "raw" / "parking_sessions" / "export_date=2026-01-31"
            partition.mkdir(parents=True)
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            rows = [
                {
                    "parking_lot_id": "lot-a",
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(days=31)).isoformat(),
                    "capacity_at_export": 100,
                }
            ]
            encoded = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
            data_file = partition / "run.jsonl"
            data_file.write_text(encoded, encoding="utf-8")
            digest = hashlib.sha256(data_file.read_bytes()).hexdigest()
            manifest = {
                "data_file": data_file.relative_to(lake).as_posix(),
                "sha256": digest,
                "record_count": 1,
            }
            (partition / "run.manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            state = lake / "_state" / "parking_sessions.json"
            state.parent.mkdir()
            state.write_text(json.dumps({"watermark": "2026-02-01T00:00:00Z"}))

            report = inspect_forecast(lake, min_history_days=30)

            self.assertTrue(report["ready"])
            self.assertEqual(report["record_count"], 1)
            self.assertEqual(report["eligible_lots"], ["lot-a"])

    def test_forecast_does_not_accept_synthetic_silver_as_raw_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lake = Path(temporary)
            silver = lake / "silver" / "parking_sessions"
            silver.mkdir(parents=True)
            (silver / "historical_occupancy_30d.json").write_text("[]")

            report = inspect_forecast(lake, min_history_days=1)

            self.assertFalse(report["ready"])
            self.assertTrue(report["synthetic_silver_files"])

    def test_vision_rejects_image_path_outside_golden_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            golden = Path(temporary) / "golden"
            golden.mkdir()
            (golden / "manifest.json").write_text(
                json.dumps(
                    {
                        "images_dir": "images",
                        "items": [
                            {
                                "file": "../../outside.jpg",
                                "plate": "51F12345",
                                "sha256": "0" * 64,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = inspect_vision(golden, min_samples=1)

            self.assertFalse(report["ready"])
            self.assertTrue(
                any("must stay inside" in error for error in report["errors"])
            )


if __name__ == "__main__":
    unittest.main()
