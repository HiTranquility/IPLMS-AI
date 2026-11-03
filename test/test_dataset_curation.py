"""Khóa hành vi tối thiểu của quality, selection và snapshot dataset."""
import unittest

import cv2
import numpy as np

from app.core.dataset.dtos import ImageQualityReport, SnapshotSample
from app.core.dataset.engines import inspect_image_quality, select_sample
from app.core.dataset import CurationService, SnapshotService


class ImageQualityTest(unittest.TestCase):
    def test_anh_rong_bi_loai_ro_ly_do(self):
        report = inspect_image_quality(b"")
        self.assertFalse(report.decoded)
        self.assertFalse(report.acceptable)
        self.assertEqual(report.reasons, ("empty",))

    def test_anh_du_kich_thuoc_va_tuong_phan_duoc_chap_nhan(self):
        image = np.zeros((120, 160, 3), dtype=np.uint8)
        image[:, 80:] = 255
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)

        report = inspect_image_quality(encoded.tobytes(), min_blur_score=0.0)

        self.assertTrue(report.decoded)
        self.assertTrue(report.acceptable)
        self.assertEqual((report.width, report.height), (160, 120))


class SampleSelectorTest(unittest.TestCase):
    def test_correction_luon_duoc_de_xuat_review(self):
        quality = ImageQualityReport(True, 640, 480, 120.0, 80.0, True)
        selected, reasons = select_sample(quality, human_corrected=True)
        self.assertTrue(selected)
        self.assertEqual(reasons, ("human_correction",))


class SnapshotServiceTest(unittest.TestCase):
    def _sample(self, sample_id: str = "capture-1") -> SnapshotSample:
        return SnapshotSample(
            sample_id=sample_id,
            object_key=f"raw/vision/{sample_id}/original.jpg",
            sha256="a" * 64,
            label="car",
            split="train",
            group_id="vehicle-1",
        )

    def test_lock_on_dinh_khi_thu_tu_dau_vao_thay_doi(self):
        first = self._sample("capture-1")
        second = self._sample("capture-2")

        lock_a = SnapshotService.build_lock("vehicle-cls-v1", [first, second])
        lock_b = SnapshotService.build_lock("vehicle-cls-v1", [second, first])

        self.assertEqual(lock_a["samples_sha256"], lock_b["samples_sha256"])
        self.assertEqual(lock_a["sample_count"], 2)

    def test_trung_sample_id_bi_chan(self):
        sample = self._sample()
        with self.assertRaisesRegex(ValueError, "duplicate sample_id"):
            SnapshotService.build_lock("vehicle-cls-v1", [sample, sample])



class EvaluateCaptureTest(unittest.TestCase):
    """ISSUE-010: một lượt check-in ở cổng qua luật chọn mẫu với chính sách của admin."""

    @staticmethod
    def _good_image() -> bytes:
        image = np.zeros((120, 160, 3), dtype=np.uint8)
        image[:, 80:] = 255
        return cv2.imencode(".jpg", image)[1].tobytes()

    def _run(self, **kw):
        base = dict(model_confidence=0.9, human_corrected=False, low_confidence_threshold=0.75, random_audit_rate=0.03)
        base.update(kw)
        return CurationService.evaluate_capture(self._good_image(), **base)

    def test_confident_good_read_is_not_selected_when_not_drawn(self):
        result = self._run(draw=lambda: 0.5)
        self.assertFalse(result.selected)

    def test_random_audit_follows_policy_rate(self):
        self.assertIn("random_audit", self._run(draw=lambda: 0.01).reasons)  # 0.01 < 3%
        self.assertNotIn("random_audit", self._run(draw=lambda: 0.05).reasons)

    def test_low_confidence_uses_policy_threshold(self):
        self.assertIn("low_confidence", self._run(model_confidence=0.6685, draw=lambda: 0.9).reasons)
        self.assertNotIn("low_confidence", self._run(model_confidence=0.6685, low_confidence_threshold=0.6, draw=lambda: 0.9).reasons)

    def test_staff_correction_is_always_selected(self):
        result = self._run(human_corrected=True, draw=lambda: 0.9)
        self.assertEqual(("human_correction",), result.reasons)


if __name__ == "__main__":
    unittest.main()
