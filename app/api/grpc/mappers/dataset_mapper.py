from app.core.console.dtos import ExportedCapture
from app.core.dataset.services.evaluation_service import EvaluationSample
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


def to_exported_captures(message):

    return [
        ExportedCapture(
            capture_id=s.capture_id.lower(),
            image_url=s.image_url,
            image_sha256=s.image_sha256.lower(),
            machine_plate=s.machine_plate,
            machine_confidence=s.machine_confidence if s.has_machine_confidence else None,
            confirmed_plate=s.confirmed_plate,
            human_corrected=s.human_corrected,
            selection_reasons=tuple(s.selection_reasons),
            status=s.status,
            purpose=s.purpose or "train",
            final_plate=s.final_plate,
            group_ref=s.group_ref.lower(),
            area_ref=s.area_ref.lower(),
            updated_at=s.updated_at,
            captured_at=s.captured_at,
        )
        for s in message.samples
    ]


def to_export_response(result: dict):
    return _pb2.ExportForConsoleResponse(
        accepted=result["accepted"],
        rejected=result["rejected"],
        watermark_at=result["watermark_at"],
        watermark_id=result["watermark_id"],
        rejected_ids=result["rejected_ids"],
    )


def to_accept_policy_response(policy: dict | None):
    if policy is None:
        return _pb2.GetAcceptPolicyResponse(found=False)
    return _pb2.GetAcceptPolicyResponse(
        found=True,
        policy_id=policy["id"],
        version=policy["version"],
        auto_accept_threshold=policy["auto_accept_threshold"],
        audit_rate=policy["audit_rate"],
        decided_at=policy["decided_at"],
    )
