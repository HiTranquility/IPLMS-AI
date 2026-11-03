"""ISSUE-013: đo ANPR trên snapshot — logic chấm + stream gRPC (engine/tải ảnh giả lập)."""
import asyncio
import unittest

from app.api.grpc.generated_stubs import STUBS_READY, get_stub
from app.core.dataset import EvalSample, eval_service as ev


def fake_run(mapping):
    def run(image: bytes):
        plate, conf = mapping[image.decode()]
        if plate is RuntimeError:
            raise RuntimeError("engine hỏng")
        return {"plate_number": plate, "confidence": conf, "process_time": 0.1}

    return run


class EvalServiceTest(unittest.TestCase):
    def _rows(self, mapping):
        samples = [EvalSample(k, f"https://cdn/{k}.jpg", v[0]) for k, v in LABELS.items()]
        run = fake_run(mapping)
        return [ev.evaluate_one(s, fetch=lambda url: url.split("/")[-1][:-4].encode(), run=run) for s in samples]

    def test_scores_like_eval_plates(self):
        rows = self._rows({"a": ("59C-888.66", 0.9), "b": ("51A00000", 0.8), "c": ("30G-111.22", 0.4)})
        summary = ev.summarize(rows)
        self.assertEqual(3, summary["total"])
        # b: nhãn 51A-000.01 ≠ 51A00000 → sai; c đúng ở mức relaxed
        self.assertAlmostEqual(2 / 3, summary["exact_match_relaxed"])
        self.assertEqual(["b"], [f["sampleId"] for f in summary["failures"]])
        self.assertEqual(2, sum(summary["confidenceBuckets"]["correct"]))
        self.assertEqual(1, summary["confidenceBuckets"]["wrong"][8])  # 0.8 → ô 8

    def test_engine_error_is_a_row_not_a_crash(self):
        rows = self._rows({"a": (RuntimeError, 0), "b": ("51A-000.01", 0.9), "c": ("30G-111.22", 0.9)})
        failed = [r for r in rows if r["error"]]
        self.assertEqual(1, len(failed))
        self.assertIn("engine hỏng", failed[0]["error"])
        self.assertEqual(1, ev.summarize(rows)["errors"])

    def test_fetch_rejects_non_http_urls(self):
        with self.assertRaises(ValueError):
            ev.fetch_image("file:///etc/passwd")


LABELS = {"a": ("59C-888.66",), "b": ("51A-000.01",), "c": ("30G-111.22",)}


@unittest.skipUnless(STUBS_READY, "Chưa sinh stub — chạy app/script/compile_proto.py")
class EvaluateSnapshotHandlerTest(unittest.TestCase):
    def test_streams_progress_then_result(self):
        from unittest import mock

        from app.api.grpc.handlers.dataset_handler import DatasetHandler

        pb2, _ = get_stub("dataset_service")
        request = pb2.EvaluateSnapshotRequest(
            evaluation_id="e1",
            samples=[pb2.EvaluationSample(sample_id="a", image_url="https://cdn/a.jpg", label="59C-888.66")],
        )

        original = ev.evaluate_one

        def fake_one(sample):
            return original(sample, fetch=lambda _u: b"a", run=fake_run({"a": ("59C-888.66", 0.9)}))

        async def collect():
            with mock.patch.object(ev, "evaluate_one", side_effect=fake_one), mock.patch.object(
                ev, "model_version", return_value="yolo:test"
            ):
                return [e async for e in DatasetHandler().EvaluateSnapshot(request, None)]

        events = asyncio.run(collect())
        self.assertEqual("progress", events[0].WhichOneof("event"))
        self.assertEqual(1, events[0].progress.done)
        self.assertEqual("result", events[-1].WhichOneof("event"))
        self.assertEqual("yolo:test", events[-1].result.model_version)
        self.assertIn('"exact_match_strict": 1.0', events[-1].result.summary_json)


if __name__ == "__main__":
    unittest.main()
