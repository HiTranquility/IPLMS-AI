"""Unit tests cho AnprOnnxEngine runtime toggle (AI Console) và script export ONNX tất định."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

try:
    import numpy as np
    import onnx
    from onnx import TensorProto, helper
    from app.config import get_config
    from app.core.vision.engines.anpr.onnx_engine import AnprOnnxEngine

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "Yêu cầu đầy đủ thư viện trong ai/.venv (numpy, onnx, app.config)")
class AnprOnnxRuntimeToggleTest(unittest.TestCase):
    """Đảm bảo cờ cfg.vision.onnx_enabled từ AI Console có hiệu lực tức thời lúc runtime."""

    def setUp(self):
        self.cfg = get_config()
        self._saved_onnx_enabled = self.cfg.vision.onnx_enabled
        self._saved_onnx_dir = self.cfg.vision.onnx_model_dir

    def tearDown(self):
        self.cfg.vision.onnx_enabled = self._saved_onnx_enabled
        self.cfg.vision.onnx_model_dir = self._saved_onnx_dir

    def test_console_toggle_disables_and_reenables_onnx_at_runtime(self):
        self.cfg.vision.onnx_enabled = True
        engine = AnprOnnxEngine(model_path="__non_existent__.onnx")

        # Gắn mock ONNX session đang hoạt động
        mock_session = MagicMock()
        out = np.zeros((1, 5, 8400), dtype=np.float32)
        out[0, :5, 0] = [320.0, 240.0, 160.0, 120.0, 0.92]
        mock_session.run.return_value = [out]
        engine.session = mock_session
        engine.input_name = "images"
        engine.output_names = ["output0"]
        engine.is_onnx_available = True

        img = np.full((480, 640, 3), 128, dtype=np.uint8)
        self.assertTrue(engine.is_using_onnx())
        crop, conf = engine.detect_plate(img)
        self.assertAlmostEqual(conf, 0.92, places=4)
        self.assertEqual(mock_session.run.call_count, 1)

        # Khi tắt onnx_enabled từ AI Console Settings, lần gọi kế tiếp phải chuyển sang PyTorch fallback
        self.cfg.vision.onnx_enabled = False
        self.assertFalse(engine.is_using_onnx())
        fallback_crop = img[10:50, 10:80]
        with patch("app.core.vision.engines.anpr.onnx_engine.pt_detect", return_value=(fallback_crop, 0.77)) as mock_pt:
            crop2, conf2 = engine.detect_plate(img)
            self.assertEqual(mock_pt.call_count, 1)
            self.assertEqual(conf2, 0.77)
            self.assertEqual(mock_session.run.call_count, 1)

        # Bật lại onnx_enabled -> dùng lại session sẵn có ngay lập tức
        self.cfg.vision.onnx_enabled = True
        self.assertTrue(engine.is_using_onnx())
        _, conf3 = engine.detect_plate(img)
        self.assertAlmostEqual(conf3, 0.92, places=4)
        self.assertEqual(mock_session.run.call_count, 2)

    def test_lazy_session_init_when_onnx_enabled_after_startup(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_onnx = Path(tmp_dir) / "best.onnx"
            fake_onnx.write_bytes(b"fake-onnx-bytes")

            self.cfg.vision.onnx_enabled = False
            fake_session = MagicMock()
            fake_session.get_inputs.return_value = [SimpleNamespace(name="images")]
            fake_session.get_outputs.return_value = [SimpleNamespace(name="output0")]

            with patch("app.core.vision.engines.anpr.onnx_engine.HAS_ONNXRUNTIME", True), patch(
                "app.core.vision.engines.anpr.onnx_engine.ort"
            ) as mock_ort:
                mock_ort.SessionOptions.return_value = MagicMock()
                mock_ort.GraphOptimizationLevel.ORT_ENABLE_ALL = 99
                mock_ort.ExecutionMode.ORT_SEQUENTIAL = 0
                mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
                mock_ort.InferenceSession.return_value = fake_session

                engine = AnprOnnxEngine(model_path=fake_onnx)
                self.assertFalse(engine.is_using_onnx())
                self.assertEqual(mock_ort.InferenceSession.call_count, 0)

                # Bật ONNX sau khi khởi động -> nạp lười đúng 1 lần
                self.cfg.vision.onnx_enabled = True
                self.assertTrue(engine.is_using_onnx())
                self.assertEqual(mock_ort.InferenceSession.call_count, 1)
                self.assertEqual(engine.resolved_onnx_path, fake_onnx)

    def test_normalize_onnx_metadata_strips_timestamp_for_deterministic_hash(self):
        from app.script.export_anpr_onnx import normalize_onnx_metadata, sha256_file

        x = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 4, 4])
        y = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 3, 4, 4])
        node = helper.make_node("Identity", ["images"], ["output0"])
        graph = helper.make_graph([node], "tiny_graph", [x], [y])

        with tempfile.TemporaryDirectory() as tmp_dir:
            p1 = Path(tmp_dir) / "m1.onnx"
            p2 = Path(tmp_dir) / "m2.onnx"

            for path, ts in ((p1, "2026-11-14T12:00:00+07:00"), (p2, "2026-11-14T12:05:99+07:00")):
                model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
                helper.set_model_props(model, {"author": "Ultralytics", "date": ts})
                onnx.save(model, str(path))
                normalize_onnx_metadata(path, source_sha256="abc123def456")

            self.assertEqual(sha256_file(p1), sha256_file(p2))


if __name__ == "__main__":
    unittest.main()
