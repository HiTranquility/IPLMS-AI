"""Tạo lock manifest ổn định từ các mẫu đã được review."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Iterable

from app.core.dataset.dtos import SnapshotSample


_ALLOWED_SPLITS = {"train", "val", "test-golden"}


class SnapshotService:
    @staticmethod
    def build_lock(dataset_id: str, samples: Iterable[SnapshotSample]) -> dict:
        ordered = sorted(samples, key=lambda sample: sample.sample_id)
        if not dataset_id.strip():
            raise ValueError("dataset_id is required")
        if not ordered:
            raise ValueError("snapshot requires at least one reviewed sample")

        seen_ids = set()
        entries = []
        for sample in ordered:
            if sample.sample_id in seen_ids:
                raise ValueError(f"duplicate sample_id: {sample.sample_id}")
            if sample.split not in _ALLOWED_SPLITS:
                raise ValueError(f"unsupported split: {sample.split}")
            seen_ids.add(sample.sample_id)
            entries.append(asdict(sample))

        canonical = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return {
            "dataset_id": dataset_id,
            "sample_count": len(entries),
            "samples_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "samples": entries,
        }
