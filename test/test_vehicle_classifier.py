"""Phân loại xe: checkpoint lệch phải tắt hẳn tầng này, đoán kém phải trả "không rõ".

Nhãn loại xe đi thẳng vào so khớp chống gian lận lúc check-out, nên nhãn rác
(trọng số ngẫu nhiên, hoặc xác suất sát ngưỡng đoán bừa) tệ hơn không có nhãn.
"""
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch
from PIL import Image

from app.core.vision.engines import vehicle_classifier


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    return buffer.getvalue()


class _FixedLogits(torch.nn.Module):
    def __init__(self, logits):
        super().__init__()
        self.logits = torch.tensor([logits])

    def forward(self, x):
        return self.logits


class VehicleClassifierTest(unittest.TestCase):
    def setUp(self):
        self._saved = dict(vehicle_classifier._state)

    def tearDown(self):
        vehicle_classifier._state.clear()
        vehicle_classifier._state.update(self._saved)

    def _use_model(self, logits, min_confidence=0.6):
        vehicle_classifier._state.update(
            init=True,
            model=_FixedLogits(logits),
            device=torch.device("cpu"),
            labels=["car_sedan", "car_suv", "motorbike", "truck"],
            min_confidence=min_confidence,
            tf=lambda image: torch.zeros(3, 4, 4),
        )

    def test_confident_prediction_returns_label(self):
        self._use_model([0.0, 0.0, 6.0, 0.0])
        self.assertEqual(vehicle_classifier.classify_vehicle(_png()), "motorbike")

    def test_low_confidence_prediction_is_unknown(self):
        # softmax ≈ [0.29, 0.21, 0.29, 0.21]: argmax vẫn ra một nhãn, nhưng đó là đoán.
        self._use_model([0.3, 0.0, 0.31, 0.0])
        self.assertIsNone(vehicle_classifier.classify_vehicle(_png()))

    def test_mismatched_checkpoint_disables_classifier(self):
        vehicle_classifier._state.update(init=False, model=None)
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "vehicle.pth"
            torch.save({"model_state_dict": {"khong.phai.lop.nao": torch.zeros(1)}}, checkpoint)
            vision = SimpleNamespace(
                vehicle_checkpoint=str(checkpoint),
                vehicle_artifact_url="",
                vehicle_artifact_sha256="",
                vehicle_model_version="v1",
                vehicle_model="NetV2",
                vehicle_num_classes=4,
                vehicle_label_list=["car_sedan", "car_suv", "motorbike", "truck"],
                vehicle_img_size=32,
                vehicle_min_confidence=0.6,
                device="cpu",
            )
            registry = SimpleNamespace(resolve=lambda spec: checkpoint)
            with patch.object(
                vehicle_classifier, "get_config", return_value=SimpleNamespace(vision=vision)
            ), patch.object(
                vehicle_classifier, "get_model_artifact_registry", return_value=registry
            ):
                self.assertIsNone(vehicle_classifier.classify_vehicle(_png()))

        self.assertTrue(vehicle_classifier._state["init"])
        self.assertIsNone(vehicle_classifier._state["model"])


if __name__ == "__main__":
    unittest.main()
