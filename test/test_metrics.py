"""Unit tests for AI Prometheus exposition metrics (`app/infra/metrics.py`)."""
from __future__ import annotations

import unittest

from app.infra.metrics import (
    observe_ai_inference,
    render_prometheus_metrics,
    track_ai_inference,
)


class MetricsTests(unittest.TestCase):
    def test_observe_ai_inference_increments_histogram_buckets(self) -> None:
        observe_ai_inference("anpr", "success", 0.04)
        text = render_prometheus_metrics()
        self.assertIn("# TYPE iplms_ai_inference_duration_seconds histogram", text)
        self.assertIn(
            'iplms_ai_inference_duration_seconds_bucket{model="anpr",status="success",le="0.05"}',
            text,
        )
        self.assertIn(
            'iplms_ai_inference_duration_seconds_count{model="anpr",status="success"}',
            text,
        )

    def test_track_ai_inference_records_error_on_exception(self) -> None:
        with self.assertRaises(RuntimeError):
            with track_ai_inference("copilot"):
                raise RuntimeError("simulated inference error")
        text = render_prometheus_metrics()
        self.assertIn(
            'iplms_ai_inference_duration_seconds_count{model="copilot",status="error"}',
            text,
        )


if __name__ == "__main__":
    unittest.main()
