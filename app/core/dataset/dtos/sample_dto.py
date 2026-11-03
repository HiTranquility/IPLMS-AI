"""DTO thuần cho curation và snapshot dataset; không phụ thuộc transport."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ImageQualityReport:
    decoded: bool
    width: int
    height: int
    brightness: float
    blur_score: float
    acceptable: bool
    reasons: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CurationResult:
    selected: bool
    reasons: Tuple[str, ...]
    quality: ImageQualityReport


@dataclass(frozen=True)
class SnapshotSample:
    sample_id: str
    object_key: str
    sha256: str
    label: str
    split: str
    group_id: Optional[str] = None


@dataclass(frozen=True)
class EvalSample:
    sample_id: str
    image_url: str
    label: str

