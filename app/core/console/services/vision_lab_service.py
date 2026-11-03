"""Gán nhãn chuyên sâu, duyệt bốn mắt và snapshot trong AI Console (ISSUE-126 P3, PROB-049 §3).

Nhãn console có provenance riêng (ADR-0048 §5): không ghi ngược về backend.
Snapshot chỉ lấy nhãn ĐÃ DUYỆT; train loại mọi nhóm đã nằm trong golden đã khoá
để không rò ảnh cùng phiên giữa train và test.
"""
from __future__ import annotations

import hashlib
import re
from typing import Optional, Sequence

from app.config import get_config
from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.core.console.engines.demo_plate_generator import DEMO_SAMPLES, generate_plate_image
from app.core.dataset import SnapshotSample, snapshot_service
from app.core.dataset.engines.plate_metrics import normalize_strict
from app.core.exceptions import ConsoleAccessDenied
from app.infra.database.console_vision_store import console_vision_store

VERDICTS = ("CORRECT", "CORRECTED", "UNUSABLE")
DECISIONS = ("APPROVED", "REJECTED")
# Khớp CHECK ck_vision_label_quality_flags và danh sách cờ ở LabelWorkspace (bug-022).
QUALITY_FLAGS = ("blurry", "glare", "skewed", "occluded", "two_line")
KINDS = ("train", "golden")
_PLATE = re.compile(r"^[0-9A-Z][0-9A-Z.\- ]{2,18}[0-9A-Z]$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_VAL_SHARE = 10  # 1/10 nhóm vào val, phần còn lại train


def _uuid(value: str, what: str) -> str:
    if not _UUID.match(value or ""):
        raise ValueError(f"{what} không hợp lệ.")
    return value


def _limit(limit: int) -> int:
    if not 1 <= limit <= 100:
        raise ValueError("Số mẫu cần trong khoảng 1–100.")
    return limit


def _reason(text: str, required: bool = True) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) > 500 or (required and len(cleaned) < 3):
        raise ValueError("Cần ghi lý do (3–500 ký tự).")
    return cleaned


def split_for(group_ref: str) -> str:
    """Chia train/val theo nhóm, tất định: cùng nhóm luôn cùng split giữa các lần snapshot."""
    bucket = int(hashlib.sha256(group_ref.encode("utf-8")).hexdigest()[:8], 16) % _VAL_SHARE
    return "val" if bucket == 0 else "train"


class VisionLabService:
    def __init__(self, store=None, demo_seed_enabled: Optional[bool] = None) -> None:
        self.store = store or console_vision_store
        self._demo_seed_enabled = demo_seed_enabled

    async def status(self, actor: ConsoleActor) -> dict:
        access_policy.require(actor, "ai:metrics:read")
        return {**await self.store.import_status(), **await self.store.label_counts()}

    async def label_queue(self, actor: ConsoleActor, limit: int = 20) -> list[dict]:
        access_policy.require(actor, "ai:task:label")
        return await self.store.label_queue(actor.member_id, _limit(limit))

    async def crop(self, capture_id: str) -> Optional[bytes]:
        """Quyền đã kiểm ở cổng REST (người gán hoặc người duyệt)."""
        return await self.store.crop(_uuid(capture_id, "capture_id"))

    async def add_label(
        self, actor: ConsoleActor, capture_id: str, verdict: str, plate_text: str = "",
        quality_flags: Sequence[str] = (),
    ) -> str:
        access_policy.require(actor, "ai:task:label")
        _uuid(capture_id, "capture_id")
        if verdict not in VERDICTS:
            raise ValueError("Nhãn chỉ nhận CORRECT, CORRECTED hoặc UNUSABLE.")
        plate: Optional[str] = None
        if verdict == "CORRECTED":
            plate = normalize_strict(plate_text)
            if not _PLATE.match(plate):
                raise ValueError("Biển số sửa cần 4–20 ký tự chữ/số (cho phép . - và khoảng trắng).")
        unknown = set(quality_flags) - set(QUALITY_FLAGS)
        if unknown:
            raise ValueError(f"Cờ ảnh không hợp lệ: {', '.join(sorted(unknown))}.")
        flags = [f for f in QUALITY_FLAGS if f in quality_flags]  # bỏ trùng, giữ thứ tự cố định
        return await self.store.add_label(capture_id, actor.member_id, verdict, plate, flags)

    async def review_queue(self, actor: ConsoleActor, limit: int = 20) -> list[dict]:
        access_policy.require(actor, "ai:label:approve")
        return await self.store.review_queue(actor.member_id, _limit(limit))

    async def decide(self, actor: ConsoleActor, label_id: str, decision: str, note: str = "") -> None:
        access_policy.require(actor, "ai:label:approve")
        _uuid(label_id, "label_id")
        if decision not in DECISIONS:
            raise ValueError("Quyết định chỉ nhận APPROVED hoặc REJECTED.")
        # Từ chối mà không nói vì sao thì người gán không sửa được cách gán.
        note = _reason(note, required=decision == "REJECTED")
        await self.store.decide_label(label_id, actor.member_id, decision, note)

    async def seed_demo_samples(self, actor: ConsoleActor, reset: bool = False) -> dict[str, int]:
        if not (access_policy.can(actor, "ai:task:label") or access_policy.can(actor, "ai:label:approve") or access_policy.can(actor, "ai:member:manage")):
            raise ConsoleAccessDenied("Bạn không có quyền thực hiện thao tác này.")
        enabled = self._demo_seed_enabled
        if enabled is None:
            enabled = get_config().console.demo_seed_enabled
        # Mẫu demo có purpose='train': bật ở production là bơm dữ liệu giả vào snapshot train.
        if not enabled:
            raise ConsoleAccessDenied("Nạp mẫu thực hành chỉ bật ở môi trường dev/sandbox.")
        samples = []
        for item in DEMO_SAMPLES:
            image = generate_plate_image(item["plate"], item["type"], item["two_line"])
            samples.append({**item, "image": image, "image_sha256": hashlib.sha256(image).hexdigest()})
        retention = get_config().console.vision_retention_days
        if reset:
            return await self.store.seed_demo_samples(actor.member_id, samples, retention, reset=True)
        return await self.store.seed_demo_samples(actor.member_id, samples, retention)

    async def list_snapshots(self, actor: ConsoleActor) -> list[dict]:
        # Người đo model cần chọn golden để chạy eval, dù không tự tạo snapshot.
        if not (access_policy.can(actor, "ai:dataset:snapshot") or access_policy.can(actor, "ai:model:evaluate")):
            raise ConsoleAccessDenied("Bạn không có quyền xem snapshot.")
        return await self.store.list_snapshots()

    async def create_snapshot(self, actor: ConsoleActor, kind: str, name: str) -> dict:
        access_policy.require(actor, "ai:dataset:snapshot")
        if kind not in KINDS:
            raise ValueError("Loại snapshot chỉ nhận train hoặc golden.")
        name = (name or "").strip()
        if not 3 <= len(name) <= 120:
            raise ValueError("Tên snapshot cần 3–120 ký tự.")
        approved = [s for s in await self.store.approved_samples() if s["verdict"] != "UNUSABLE"]
        if kind == "train":
            golden_groups = await self.store.frozen_golden_groups()
            approved = [s for s in approved if s["group_ref"] not in golden_groups]
        samples = [
            SnapshotSample(
                sample_id=s["capture_id"],
                object_key=f"ai_console/vision_crop/{s['capture_id']}",
                sha256=s["sha256"],
                label=normalize_strict(s["plate_text"] if s["verdict"] == "CORRECTED" else s["confirmed_plate"]),
                split="test-golden" if kind == "golden" else split_for(s["group_ref"]),
                group_id=s["group_ref"],
            )
            for s in approved
        ]
        lock = snapshot_service.build_lock(name, samples)  # rỗng → ValueError
        snapshot_id = await self.store.create_snapshot(kind, name, lock, actor.member_id)
        return {"id": snapshot_id, "sample_count": lock["sample_count"], "samples_sha256": lock["samples_sha256"]}

    async def freeze(self, actor: ConsoleActor, snapshot_id: str, reason: str) -> None:
        # Step-up kiểm ở cổng REST (`ai:golden:freeze` thuộc STEP_UP_PERMISSIONS).
        access_policy.require(actor, "ai:golden:freeze")
        await self.store.freeze_snapshot(_uuid(snapshot_id, "snapshot_id"), actor.member_id, _reason(reason))


vision_lab_service = VisionLabService()
