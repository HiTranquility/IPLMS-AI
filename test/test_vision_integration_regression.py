"""Integration regression guards without model loading, artifacts or real imagery."""
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from app.core.vision.engines.anpr import engine as anpr_engine
from app.core.vision.engines import vehicle_classifier
from app.core.vision.engines.anpr.plate_text import correct_plate_confusions, plate_key
from app.core.vision.dtos.vision_dto import AnprItem, PlateResult


class PlatePreservationTest(unittest.TestCase):
    def test_valid_motorbike_series_and_all_digits_survive_correction(self):
        for plate in ("59-V1-793.79", "29-B1-123.45", "51LD-123.45", "TM-12-34"):
            with self.subTest(plate=plate):
                self.assertEqual(correct_plate_confusions(plate), plate)

    def test_correction_never_truncates_or_inserts_characters(self):
        for plate in ("59V179379", "50H1234567", "30A123456789", "59-V1-793.79-4"):
            with self.subTest(plate=plate):
                self.assertEqual(len(plate_key(correct_plate_confusions(plate))), len(plate_key(plate)))


class PipelineObservationTest(unittest.TestCase):
    def setUp(self):
        self.image = np.full((160, 320, 3), (20, 200, 240), dtype=np.uint8)
        self.data = cv2.imencode(".png", self.image)[1].tobytes()

    def test_no_detector_has_no_observed_plate_color(self):
        with patch.object(anpr_engine.model_loader, "ensure_models_loaded"), patch.object(
            anpr_engine, "get_anpr_detector"
        ) as detector, patch.object(anpr_engine, "read_plate_details", return_value=("", 0, False, {})):
            detector.return_value.detect_plate.side_effect = lambda image: (image, None)
            result = anpr_engine.run_anpr(self.data)
        self.assertEqual((result["plate_number"], result["confidence"]), ("UNKNOWN", 0.0))
        self.assertIsNone(result["plate_color"])

    def test_strong_raw_crop_keeps_color_evidence_and_skips_enhancement(self):
        crop = self.image[20:140, 30:290].copy()
        with patch.object(anpr_engine.model_loader, "ensure_models_loaded"), patch.object(
            anpr_engine, "get_anpr_detector"
        ) as detector, patch.object(
            anpr_engine, "read_plate_details", return_value=("59-V1-793.79", 0.95, True, {})
        ) as reader, patch.object(anpr_engine, "enhance_for_ocr") as enhance:
            detector.return_value.detect_plate.return_value = (crop, 0.9)
            result = anpr_engine.run_anpr(self.data)
        self.assertEqual(result["plate_number"], "59-V1-793.79")
        self.assertEqual(result["plate_color"], "yellow")
        self.assertTrue(result["is_two_line"])
        reader.assert_called_once()
        enhance.assert_not_called()
        evidence = cv2.imdecode(np.frombuffer(result["crop_bytes"], np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(evidence.shape, crop.shape)
        self.assertLess(np.abs(evidence.astype(float) - crop).mean(), 3)

    def test_dto_does_not_default_missing_measurement_to_white(self):
        result = PlateResult("UNKNOWN", "", "synthetic", "2026-10-15T00:00:00Z")
        self.assertIsNone(AnprItem.from_result(result).plate_color)


class VehicleMetadataBoundaryTest(unittest.TestCase):
    def test_plate_metadata_does_not_replace_cnn_evidence_or_confidence_gate(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch not installed")
        image_data = cv2.imencode(".png", np.full((8, 8, 3), 200, np.uint8))[1].tobytes()
        state = dict(
            init=True, device="cpu", labels=["car_sedan", "car_suv", "motorbike", "truck"],
            min_confidence=0.6, tf=lambda image: torch.zeros(3, 4, 4),
        )
        for logits, expected in (([0., 6., 0., 0.], "car_suv"), ([0., 0., 0., 0.], None)):
            with self.subTest(logits=logits), patch.dict(vehicle_classifier._state, state), patch.dict(
                vehicle_classifier._state, model=lambda image: torch.tensor([logits])
            ):
                self.assertEqual(vehicle_classifier.classify_vehicle(
                    image_data, plate_number="50H-123.45", plate_color="yellow"
                ), expected)


if __name__ == "__main__":
    unittest.main()
