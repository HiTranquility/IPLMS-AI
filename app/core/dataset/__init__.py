"""Domain dataset: curation, snapshot golden set và đánh giá độ chính xác ANPR."""
from app.core.dataset.dtos import (
    CurationResult,
    EvaluationSample,
    ImageQualityReport,
    SnapshotSample,
)

__all__ = [
    "CurationResult",
    "CurationService",
    "EvaluationSample",
    "ImageQualityReport",
    "SnapshotSample",
    "SnapshotService",
    "evaluation_service",
]


def __getattr__(name: str):
    if name in ("CurationService", "SnapshotService", "evaluation_service"):
        from app.core.dataset import services

        return getattr(services, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
