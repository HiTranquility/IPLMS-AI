"""Nạp model ANPR: lỗi nạp OCR phải được thử lại, không được khoá chết tiến trình (bug-006)."""
import sys
import types
import unittest
from unittest.mock import patch

from app.core.vision.engines.anpr import models as anpr_models
from app.infra.model_registry import ArtifactResolutionError


class EnsureModelsLoadedTest(unittest.TestCase):
    def setUp(self):
        self._saved = dict(anpr_models._state)
        anpr_models._state.update(yolo_model=None, ocr_reader=None, initialized=False)

    def tearDown(self):
        anpr_models._state.update(self._saved)

    def test_ocr_failure_is_retried_on_next_call(self):
        attempts = []

        class FlakyReader:
            def __init__(self, *args, **kwargs):
                attempts.append(1)
                if len(attempts) == 1:
                    # Đúng lỗi thật: hai tiến trình cùng tải vào chung temp.zip.
                    raise FileNotFoundError("/app/var/easyocr-cache/temp.zip")

        fake_easyocr = types.SimpleNamespace(Reader=FlakyReader)
        no_yolo = patch.object(
            anpr_models,
            "get_model_artifact_registry",
            side_effect=ArtifactResolutionError("không có best.pt trong test"),
        )
        with patch.dict(sys.modules, {"easyocr": fake_easyocr}), no_yolo:
            self.assertFalse(anpr_models.warmup())
            self.assertFalse(anpr_models._state["initialized"])

            self.assertTrue(anpr_models.warmup())
            self.assertTrue(anpr_models._state["initialized"])

        self.assertEqual(2, len(attempts))


if __name__ == "__main__":
    unittest.main()
