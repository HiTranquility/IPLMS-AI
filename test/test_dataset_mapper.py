"""Mapper + handler gRPC của DatasetService (ISSUE-010).

Backend tin nguyên văn `manifest_json` và danh sách lý do chọn ảnh — lệch tên
trường ở đây là dữ liệu sai lặng lẽ trong DB, không phải lỗi build.
"""
import asyncio
import json
import unittest

import cv2
import numpy as np

from app.api.grpc.generated_stubs import STUBS_READY, get_stub
from app.core.dataset.dtos import CurationResult, ImageQualityReport


@unittest.skipUnless(STUBS_READY, "Chưa sinh stub — chạy app/script/compile_proto.py")
class DatasetMapperTest(unittest.TestCase):
    def setUp(self):
        from app.api.grpc.mappers import dataset_mapper

        self.mapper = dataset_mapper
        self.pb2, _ = get_stub("dataset_service")

    def test_evaluate_response_keeps_reasons_and_quality(self):
        result = CurationResult(
            selected=True,
            reasons=("human_correction", "quality_edge_case"),
            quality=ImageQualityReport(
                decoded=True, width=376, height=188, brightness=21.5, blur_score=3.2,
                acceptable=False, reasons=("too_dark", "too_blurry"),
            ),
        )
        msg = self.mapper.to_evaluate_response(result)
        self.assertTrue(msg.selected)
        self.assertEqual(["human_correction", "quality_edge_case"], list(msg.reasons))
        self.assertEqual((376, 188), (msg.quality.width, msg.quality.height))
        self.assertEqual(["too_dark", "too_blurry"], list(msg.quality.reasons))
        self.assertFalse(msg.quality.acceptable)

    def test_snapshot_samples_empty_group_becomes_none(self):
        request = self.pb2.BuildSnapshotRequest(
            dataset_id="anpr-1",
            samples=[
                self.pb2.SnapshotSample(sample_id="a", object_key="k", sha256="f" * 64, label="59C88866", split="train"),
                self.pb2.SnapshotSample(sample_id="b", object_key="k2", sha256="e" * 64, label="51A00000", split="test-golden", group_id="sess-1"),
            ],
        )
        samples = self.mapper.to_snapshot_samples(request)
        self.assertIsNone(samples[0].group_id)
        self.assertEqual("sess-1", samples[1].group_id)

    def test_snapshot_response_manifest_is_the_full_lock(self):
        lock = {"dataset_id": "anpr-1", "sample_count": 1, "samples_sha256": "a" * 64, "samples": [{"label": "59C88866"}]}
        msg = self.mapper.to_snapshot_response(lock)
        self.assertEqual("anpr-1", msg.dataset_id)
        self.assertEqual(1, msg.sample_count)
        self.assertEqual(lock, json.loads(msg.manifest_json))


@unittest.skipUnless(STUBS_READY, "Chưa sinh stub — chạy app/script/compile_proto.py")
class DatasetHandlerTest(unittest.TestCase):
    def setUp(self):
        from app.api.grpc.handlers.dataset_handler import DatasetHandler

        self.handler = DatasetHandler()
        self.pb2, _ = get_stub("dataset_service")

    @staticmethod
    def _image() -> bytes:
        image = np.zeros((120, 160, 3), dtype=np.uint8)
        image[:, 80:] = 255
        return cv2.imencode(".jpg", image)[1].tobytes()

    def _evaluate(self, **kw):
        request = self.pb2.EvaluateCaptureRequest(image_data=self._image(), **kw)
        return asyncio.run(self.handler.EvaluateCapture(request, None))

    def test_missing_confidence_is_not_treated_as_low(self):
        # has_model_confidence=False: model_confidence=0 mặc định KHÔNG được coi là "điểm thấp".
        res = self._evaluate(has_model_confidence=False, random_audit_rate=0.0)
        self.assertNotIn("low_confidence", res.reasons)

    def test_zero_threshold_falls_back_to_default(self):
        # Proto3 không phân biệt "không gửi" với 0 → ngưỡng 0 nghĩa là dùng mặc định 0.75.
        res = self._evaluate(model_confidence=0.6685, has_model_confidence=True, random_audit_rate=0.0)
        self.assertIn("low_confidence", res.reasons)

    def test_audit_rate_one_always_samples_good_image(self):
        res = self._evaluate(model_confidence=0.99, has_model_confidence=True, low_confidence_threshold=0.75, random_audit_rate=1.0)
        self.assertTrue(res.selected)
        self.assertIn("random_audit", res.reasons)

    def test_build_snapshot_rejects_bad_split(self):
        request = self.pb2.BuildSnapshotRequest(
            dataset_id="x",
            samples=[self.pb2.SnapshotSample(sample_id="a", object_key="k", sha256="f" * 64, label="L", split="holdout")],
        )
        with self.assertRaises(ValueError):
            asyncio.run(self.handler.BuildSnapshot(request, None))


if __name__ == "__main__":
    unittest.main()
