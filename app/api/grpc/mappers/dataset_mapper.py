"""Map protobuf DatasetService ↔ DTO domain dataset."""
import json
from typing import List

from app.api.grpc.generated_stubs import get_stub
from app.core.dataset.dtos import CurationResult, SnapshotSample

_pb2, _ = get_stub("dataset_service")


def to_evaluate_response(result: CurationResult):
    q = result.quality
    return _pb2.EvaluateCaptureResponse(
        selected=result.selected,
        reasons=list(result.reasons),
        quality=_pb2.ImageQuality(
            decoded=q.decoded,
            width=q.width,
            height=q.height,
            brightness=q.brightness,
            blur_score=q.blur_score,
            acceptable=q.acceptable,
            reasons=list(q.reasons),
        ),
    )


def to_snapshot_samples(message) -> List[SnapshotSample]:
    return [
        SnapshotSample(
            sample_id=s.sample_id,
            object_key=s.object_key,
            sha256=s.sha256,
            label=s.label,
            split=s.split,
            group_id=s.group_id or None,
        )
        for s in message.samples
    ]


def to_evaluation_samples(message):
    from app.core.dataset.services.evaluation_service import EvaluationSample

    return [
        EvaluationSample(sample_id=s.sample_id, image_url=s.image_url, label=s.label)
        for s in message.samples
    ]


def to_progress_event(done: int, total: int):
    return _pb2.EvaluateSnapshotEvent(progress=_pb2.EvaluationProgress(done=done, total=total))


def to_result_event(model_version: str, summary: dict):
    return _pb2.EvaluateSnapshotEvent(
        result=_pb2.EvaluationResult(
            model_version=model_version,
            summary_json=json.dumps(summary, ensure_ascii=False, sort_keys=True),
        )
    )


def to_snapshot_response(lock: dict):
    return _pb2.BuildSnapshotResponse(
        dataset_id=lock["dataset_id"],
        sample_count=lock["sample_count"],
        samples_sha256=lock["samples_sha256"],
        manifest_json=json.dumps(lock, ensure_ascii=False, sort_keys=True),
    )
