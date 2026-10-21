"""Unit tests cho bộ công cụ benchmark đo lường độ trễ ANPR (PyTorch vs ONNX Runtime)."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

try:
    import cv2
    import numpy as np
    from benchmark.benchmark_anpr_latency import (
        SimulatedOnnxSession,
        benchmark_single_engine,
        calculate_percentile,
        generate_synthetic_motorbike_2line_plate,
        init_onnx_engine,
        init_pytorch_engine,
        load_or_generate_car_1line_plate,
        load_or_generate_test_images,
        run_full_benchmark,
    )

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


if not HAS_DEPS:
    import subprocess

    class DelegatedVenvTest(unittest.TestCase):
        def test_run_in_venv(self):
            ai_root = Path(__file__).resolve().parent.parent
            venv_py = ai_root / ".venv" / "Scripts" / "python.exe"
            if venv_py.exists():
                res = subprocess.run([str(venv_py), "-m", "unittest", "test.test_anpr_benchmark"], cwd=str(ai_root))
                self.assertEqual(res.returncode, 0)
            else:
                self.skipTest("ai/.venv not found")


@unittest.skipUnless(HAS_DEPS, "Yêu cầu đầy đủ thư viện trong ai/.venv (cv2, numpy, torch)")
class AnprBenchmarkUnitTest(unittest.TestCase):
    """Kiểm thử toàn diện các module của runner benchmark."""

    def setUp(self):
        from app.core.vision.engines.anpr import models as anpr_models
        from app.infra.ocr import reader as ocr_reader_module

        self._saved_anpr_state = dict(anpr_models._state)
        self._saved_reader = ocr_reader_module._reader

    def tearDown(self):
        from app.core.vision.engines.anpr import models as anpr_models
        from app.infra.ocr import reader as ocr_reader_module

        anpr_models._state.update(self._saved_anpr_state)
        ocr_reader_module._reader = self._saved_reader

    def test_calculate_percentile(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        self.assertEqual(50.0, calculate_percentile(values, 0.50))
        self.assertEqual(100.0, calculate_percentile(values, 0.95))
        self.assertEqual(100.0, calculate_percentile(values, 0.99))
        self.assertEqual(0.0, calculate_percentile([], 0.50))

    def test_synthetic_motorbike_generation(self):
        img = generate_synthetic_motorbike_2line_plate()
        self.assertIsInstance(img, np.ndarray)
        self.assertEqual(3, img.ndim)
        self.assertEqual((480, 640, 3), img.shape)
        self.assertEqual(np.uint8, img.dtype)

    def test_car_1line_plate_loading_or_generation(self):
        img, source = load_or_generate_car_1line_plate()
        self.assertIsInstance(img, np.ndarray)
        self.assertEqual(3, img.ndim)
        self.assertGreater(img.shape[0], 0)
        self.assertGreater(img.shape[1], 0)
        self.assertIsInstance(source, str)

    def test_load_or_generate_test_images_batch(self):
        batch = load_or_generate_test_images()
        self.assertIn("car_1line", batch)
        self.assertIn("motorbike_2line", batch)

        for key in ("car_1line", "motorbike_2line"):
            item = batch[key]
            self.assertIn("name", item)
            self.assertIn("format", item)
            self.assertIn("source", item)
            self.assertIn("image", item)
            self.assertIn("shape", item)
            self.assertIsInstance(item["image"], np.ndarray)

    def test_simulated_onnx_session(self):
        session = SimulatedOnnxSession(
            sim_latency_ms=0.0,
            detected_cx=320.0,
            detected_cy=240.0,
            detected_w=160.0,
            detected_h=120.0,
            detected_conf=0.95,
        )
        inputs = session.get_inputs()
        outputs = session.get_outputs()
        self.assertEqual("images", inputs[0].name)
        self.assertEqual("output0", outputs[0].name)

        feed = {"images": np.zeros((1, 3, 640, 640), dtype=np.float32)}
        out = session.run(["output0"], feed)
        self.assertEqual(1, len(out))
        self.assertEqual((1, 5, 8400), out[0].shape)
        self.assertEqual(0.95, out[0][0, 4, 0])

    def test_benchmark_single_engine_computes_metrics(self):
        dummy_img = np.full((100, 100, 3), 128, dtype=np.uint8)

        def dummy_detect(img):
            return img, 0.9

        res = benchmark_single_engine(
            engine_name="TestEngine",
            detect_fn=dummy_detect,
            image=dummy_img,
            warmup=1,
            iterations=3,
        )

        for key in ("engine_name", "iterations", "mean_ms", "p50_ms", "p95_ms", "p99_ms", "fps", "total_wall_sec"):
            self.assertIn(key, res)
        self.assertEqual(3, res["iterations"])
        self.assertGreaterEqual(res["mean_ms"], 0.0)
        self.assertGreater(res["fps"], 0.0)

    def test_submillisecond_mean_retains_precision_for_ratios(self):
        image = np.zeros((4, 4, 3), dtype=np.uint8)
        with patch("benchmark.benchmark_anpr_latency.time.perf_counter", side_effect=[0.0, 0.001, 0.0010001, 0.002]):
            result = benchmark_single_engine("synthetic", lambda value: (value, None), image, warmup=0, iterations=1)
        self.assertGreater(result["mean_ms"], 0.0)
        self.assertLess(result["mean_ms"], 0.005)

    def test_run_full_benchmark_quick_and_report_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_report = Path(tmp_dir) / "test_report.md"
            # This is a report/unit fixture: never inspect local photos or load model weights.
            synthetic = generate_synthetic_motorbike_2line_plate()
            batch = {key: {"name": key, "format": "synthetic", "source": "unit fixture", "image": synthetic, "shape": synthetic.shape} for key in ("car_1line", "motorbike_2line")}
            with patch("benchmark.benchmark_anpr_latency.load_or_generate_test_images", return_value=batch), patch("benchmark.benchmark_anpr_latency.init_pytorch_engine", return_value=(lambda image: (image, 0.9), "PyTorch YOLOv8n (CPU) synthetic fixture")), patch("benchmark.benchmark_anpr_latency.init_onnx_engine", return_value=(SimpleNamespace(detect_plate=lambda image: (image, 0.9)), "ONNX Runtime synthetic fixture")):
                results = run_full_benchmark(
                    iterations=2,
                    warmup=1,
                    output_path=tmp_report,
                    sim_latency_ms=1.0,
                )

            self.assertIn("timestamp", results)
            self.assertIn("benchmarks", results)
            self.assertIn("car_1line", results["benchmarks"])
            self.assertIn("motorbike_2line", results["benchmarks"])

            for cat in ("car_1line", "motorbike_2line"):
                bench = results["benchmarks"][cat]
                self.assertIn("pytorch", bench)
                self.assertIn("onnx", bench)
                self.assertIn("speedup_factor", bench)
                self.assertGreater(bench["speedup_factor"], 0.0)

            self.assertTrue(tmp_report.exists())
            content = tmp_report.read_text(encoding="utf-8")
            self.assertIn("# Báo Cáo Đo Lường & Benchmark Độ Trễ ANPR", content)
            self.assertIn("PyTorch YOLOv8n (CPU)", content)
            self.assertIn("ONNX Runtime", content)


if __name__ == "__main__":
    unittest.main()
