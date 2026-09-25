from __future__ import annotations

import unittest

from app.util.request_metrics import (
    distribution,
    evaluate_gates,
    normalize_plate,
    percentile,
    summarize_requests,
)


class RequestMetricsTest(unittest.TestCase):
    def test_percentile_uses_nearest_rank(self) -> None:
        values = [40, 10, 30, 20]

        self.assertEqual(percentile(values, 0.50), 20)
        self.assertEqual(percentile(values, 0.95), 40)
        self.assertEqual(distribution(values)["mean"], 25)

    def test_summary_counts_errors_latency_and_plate_accuracy(self) -> None:
        samples = [
            {
                "ok": True,
                "grpc_status": "OK",
                "rtt_ms": 100,
                "server_process_ms": 80,
                "transport_overhead_ms": 20,
                "plate_number": "51F178.12",
                "confidence": 0.9,
            },
            {
                "ok": True,
                "grpc_status": "OK",
                "rtt_ms": 200,
                "server_process_ms": 150,
                "transport_overhead_ms": 50,
                "plate_number": "51F-178.12",
                "confidence": 0.8,
            },
            {
                "ok": False,
                "grpc_status": "NOT_FOUND",
                "rtt_ms": 50,
                "server_process_ms": 0,
                "transport_overhead_ms": 0,
            },
        ]

        summary = summarize_requests(
            samples,
            wall_time_seconds=0.5,
            expected_plate="51F-178.12",
        )

        self.assertEqual(summary["successful"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertAlmostEqual(summary["error_rate"], 1 / 3)
        self.assertEqual(summary["throughput_rps"], 6)
        self.assertEqual(summary["rtt_ms"]["p95"], 200)
        self.assertAlmostEqual(summary["strict_match_rate"], 1 / 3)
        self.assertAlmostEqual(summary["normalized_match_rate"], 2 / 3)

    def test_gates_report_every_failed_condition(self) -> None:
        summary = {
            "error_rate": 0.2,
            "rtt_ms": {"p95": 1200},
            "normalized_match_rate": 0.8,
        }

        failures = evaluate_gates(
            summary,
            max_error_rate=0.1,
            max_p95_ms=1000,
            min_normalized_match_rate=0.9,
        )

        self.assertEqual(len(failures), 3)

    def test_plate_normalization_only_removes_format_separators(self) -> None:
        self.assertEqual(normalize_plate("51f-178.12"), "51F17812")


if __name__ == "__main__":
    unittest.main()
