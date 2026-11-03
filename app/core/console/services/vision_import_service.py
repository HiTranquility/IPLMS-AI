"""Nhận dữ liệu ANPR backend đẩy sang AI Console qua kênh A2 (IPLMS ADR-0048 §5).

Backend không giữ trạng thái: hỏi watermark (lượt rỗng) rồi gửi các mẫu có
(updated_at, capture_id) lớn hơn. Mỗi lượt idempotent theo `capture_id`. Ảnh cắt
được tải về DB console và so sha256 — sai thì loại mẫu đó, không làm hỏng cả lượt.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import urllib.error
from datetime import datetime
from typing import Callable, Iterable, Optional

from app.config import get_config
from app.core.console.dtos import ExportedCapture
from app.core.dataset.services.eval_service import fetch_image
from app.infra.database.console_vision_store import console_vision_store
from app.util.logger import logger

MAX_BATCH = 200
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = {"PENDING", "LABELED", "CONFIRMED", "DISPUTED", "DISCARDED"}
_PURPOSES = {"train", "golden"}
_PLATE_MAX = 20


def _instant(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field} không phải ISO-8601") from None
    if parsed.tzinfo is None:
        raise ValueError(f"{field} thiếu múi giờ")
    return parsed


def _validate(sample: ExportedCapture) -> dict:
    """Mẫu sai hợp đồng → ValueError (cả lượt INVALID_ARGUMENT: lỗi ở phía gửi, không phải dữ liệu)."""
    if not _UUID.match(sample.capture_id):
        raise ValueError("capture_id phải là UUID chữ thường")
    if not _HEX64.match(sample.image_sha256):
        raise ValueError(f"image_sha256 không hợp lệ ({sample.capture_id})")
    for ref in (sample.group_ref, sample.area_ref):
        if ref and not _HEX64.match(ref):
            # Chặn backend lỡ gửi id dạng rõ thay cho HMAC.
            raise ValueError(f"group_ref/area_ref phải là HMAC hex 64 ký tự ({sample.capture_id})")
    if sample.status not in _STATUSES or sample.purpose not in _PURPOSES:
        raise ValueError(f"status/purpose không hợp lệ ({sample.capture_id})")
    if sample.machine_confidence is not None and not 0.0 <= sample.machine_confidence <= 1.0:
        raise ValueError(f"machine_confidence ngoài 0..1 ({sample.capture_id})")
    plates = (sample.machine_plate, sample.confirmed_plate, sample.final_plate)
    if any(len(p) > _PLATE_MAX for p in plates):
        raise ValueError(f"biển số quá dài ({sample.capture_id})")
    updated_at = _instant(sample.updated_at, "updated_at")
    captured_at = _instant(sample.captured_at, "captured_at") if sample.captured_at else None
    return {
        "capture_id": sample.capture_id, "image_sha256": sample.image_sha256,
        "machine_plate": sample.machine_plate, "machine_confidence": sample.machine_confidence,
        "confirmed_plate": sample.confirmed_plate, "human_corrected": sample.human_corrected,
        "selection_reasons": [r[:40] for r in sample.selection_reasons][:10],
        "status": sample.status, "purpose": sample.purpose,
        "final_plate": sample.final_plate or None, "group_ref": sample.group_ref or None,
        "area_ref": sample.area_ref or None, "captured_at": captured_at, "updated_at": updated_at,
    }


def _permanent(exc: Exception) -> bool:
    """Lỗi không tự hết khi gửi lại: ảnh sai/hỏng/quá lớn, hoặc Storage trả 4xx."""
    if isinstance(exc, urllib.error.HTTPError):
        return 400 <= exc.code < 500
    return isinstance(exc, ValueError)


class VisionImportService:
    def __init__(self, store=None, fetch: Callable[[str], bytes] = fetch_image, retention_days: Optional[int] = None) -> None:
        self.store = store or console_vision_store
        self._fetch = fetch
        self._retention_days = retention_days

    def _retention(self) -> int:
        return self._retention_days or get_config().console.vision_retention_days

    async def _download(self, sample: ExportedCapture) -> bytes:
        image = await asyncio.to_thread(self._fetch, sample.image_url)
        if hashlib.sha256(image).hexdigest() != sample.image_sha256:
            raise ValueError("sha256 ảnh không khớp")
        return image

    async def import_batch(self, samples: Iterable[ExportedCapture]) -> dict:
        samples = list(samples)
        if len(samples) > MAX_BATCH:
            raise ValueError(f"Tối đa {MAX_BATCH} mẫu một lượt.")
        current = await self.store.import_watermark()
        if not samples:
            return self._result(0, [], current)

        pairs = sorted(((s, _validate(s)) for s in samples), key=lambda p: (p[1]["updated_at"], p[1]["capture_id"]))
        rows = [row for _, row in pairs]
        if len({r["capture_id"] for r in rows}) != len(rows):
            raise ValueError("capture_id trùng trong cùng một lượt")
        have = await self.store.existing_crops([r["capture_id"] for r in rows])
        accepted, crops, rejects = [], {}, []
        # Con trỏ chỉ vượt qua mẫu đã xử lý xong: lỗi tạm (mạng, 5xx) dừng con trỏ trước mẫu
        # đó để backend gửi lại lượt sau; lỗi vĩnh viễn (sha256 lệch, 4xx) ghi lỗi rồi đi tiếp.
        cursor = None
        blocked = False
        for sample, row in pairs:
            if row["capture_id"] not in have:
                try:
                    crops[row["capture_id"]] = await self._download(sample)
                except Exception as exc:  # noqa: BLE001 — một ảnh lỗi không hỏng cả lượt
                    rejects.append((row["capture_id"], f"{type(exc).__name__}: {exc}"))
                    blocked = blocked or not _permanent(exc)
                    if not blocked:
                        cursor = (row["updated_at"], row["capture_id"])
                    continue
            accepted.append(row)
            if not blocked:
                cursor = (row["updated_at"], row["capture_id"])

        if current is not None:
            current_key = (_instant(current[0], "watermark"), current[1])
            cursor = max(current_key, cursor) if cursor else current_key
        # cursor None = mẫu đầu đã lỗi tạm và console chưa có mốc nào: giữ nguyên, lượt sau gửi lại.
        await self.store.import_batch(accepted, crops, rejects, cursor, self._retention())
        if rejects:
            logger.warning("Console A2: loại %d/%d mẫu", len(rejects), len(rows))
        watermark = (cursor[0].isoformat(), cursor[1]) if cursor else None
        return self._result(len(accepted), [cid for cid, _ in rejects], watermark)

    @staticmethod
    def _result(accepted: int, rejected_ids: list[str], watermark) -> dict:
        return {
            "accepted": accepted,
            "rejected": len(rejected_ids),
            "rejected_ids": rejected_ids,
            "watermark_at": watermark[0] if watermark else "",
            "watermark_id": watermark[1] if watermark else "",
        }


vision_import_service = VisionImportService()
