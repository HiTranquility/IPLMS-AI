"""Phiên bản model, lượt đo trên golden đã khoá và promote bốn mắt (ISSUE-126 P4, PROB-049 §3).

Lượt đo chạy ĐÚNG engine đang nạp trên AI host (`eval_service`) với ảnh cắt
lấy từ DB console. Model chỉ được đề xuất khi đã có lượt đo xong trên golden đã
khoá mà weights khớp `sha256` của model — không đo thì không có số để duyệt.
"""
from __future__ import annotations

import asyncio
import re
from typing import Callable, Dict, Optional

from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy
from app.core.dataset import EvalSample, eval_service
from app.infra.database.console_vision_store import console_vision_store
from app.util.logger import logger

_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,63}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _reason(text: str) -> str:
    cleaned = (text or "").strip()
    if not 3 <= len(cleaned) <= 500:
        raise ValueError("Cần ghi lý do (3–500 ký tự).")
    return cleaned


def _uuid(value: str, what: str) -> str:
    if not _UUID.match(value or ""):
        raise ValueError(f"{what} không hợp lệ.")
    return value


class ModelLabService:
    def __init__(
        self, store=None,
        run: Optional[Callable[[bytes], Dict[str, object]]] = None,
        engine_version: Optional[Callable[[], str]] = None,
    ) -> None:
        self.store = store or console_vision_store
        self._run = run
        self._engine_version = engine_version or eval_service.model_version
        self._tasks: set[asyncio.Task] = set()

    async def list_models(self, actor: ConsoleActor) -> list[dict]:
        access_policy.require(actor, "ai:metrics:read")
        return await self.store.list_models()

    async def register(self, actor: ConsoleActor, data: dict) -> str:
        access_policy.require(actor, "ai:model:propose")
        name = (data.get("name") or "").strip().lower()
        version = (data.get("version") or "").strip()
        artifact_key = (data.get("artifact_key") or "").strip()
        sha256 = (data.get("sha256") or "").strip().lower()
        if not _NAME.match(name):
            raise ValueError("Tên model: chữ thường, số, . _ - (2–64 ký tự).")
        if not 1 <= len(version) <= 64:
            raise ValueError("Phiên bản cần 1–64 ký tự.")
        if not artifact_key.startswith("models/") or len(artifact_key) > 500 or ".." in artifact_key:
            # Đúng prefix lưu trữ PROB-049 §2: models/<name>/<version>/…
            raise ValueError("artifact_key phải nằm dưới models/ (PROB-049 §2).")
        if not _HEX64.match(sha256):
            raise ValueError("sha256 của weights cần 64 ký tự hex.")
        snapshot_id = data.get("train_snapshot_id") or None
        if snapshot_id:
            _uuid(snapshot_id, "train_snapshot_id")
        return await self.store.register_model(
            {"name": name, "version": version, "artifact_key": artifact_key, "sha256": sha256,
             "train_snapshot_id": snapshot_id, "note": (data.get("note") or "").strip()[:500]},
            actor.member_id,
        )

    async def propose(self, actor: ConsoleActor, model_id: str, reason: str) -> None:
        access_policy.require(actor, "ai:model:propose")
        model = await self.store.get_model(_uuid(model_id, "model_id"))
        if model is None:
            raise ValueError("Không tìm thấy model.")
        if not await self.store.evals_for_engine_digest(model["sha256"][:12]):
            raise ValueError(
                "Chưa có lượt đo xong trên golden đã khoá với weights của model này — đo trước rồi mới đề xuất."
            )
        await self.store.propose_model(model_id, actor.member_id, _reason(reason))

    async def promote(self, actor: ConsoleActor, model_id: str, reason: str) -> None:
        # Step-up kiểm ở cổng REST; bốn mắt kiểm ở đây và trong transaction của store.
        access_policy.require(actor, "ai:model:promote")
        model = await self.store.get_model(_uuid(model_id, "model_id"))
        if model is None:
            raise ValueError("Không tìm thấy model.")
        access_policy.require_second_person(actor, model["proposed_by_id"])
        await self.store.promote_model(model_id, actor.member_id, _reason(reason))

    async def list_evals(self, actor: ConsoleActor) -> list[dict]:
        access_policy.require(actor, "ai:metrics:read")
        return await self.store.list_evals()

    async def start_eval(self, actor: ConsoleActor, snapshot_id: str) -> str:
        access_policy.require(actor, "ai:model:evaluate")
        snapshot = await self.store.get_snapshot(_uuid(snapshot_id, "snapshot_id"))
        if snapshot is None:
            raise ValueError("Không tìm thấy snapshot.")
        if snapshot["kind"] != "golden" or snapshot["frozen_at"] is None:
            raise ValueError("Chỉ đo trên snapshot golden đã khoá — thước đo phải đứng yên.")
        samples = [
            EvalSample(sample_id=s["sample_id"], image_url=s["sample_id"], label=s["label"])
            for s in snapshot["manifest"]["samples"]
            if s["split"] == "test-golden"
        ]
        if not samples:
            raise ValueError("Snapshot không có mẫu test-golden nào để đo.")
        run_id = await self.store.start_eval(snapshot_id, actor.member_id)
        task = asyncio.get_running_loop().create_task(self._evaluate(run_id, samples))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run_id

    async def _evaluate(self, run_id: str, samples: list[EvalSample]) -> None:
        loop = asyncio.get_running_loop()

        def fetch(capture_id: str) -> bytes:
            # `image_url` mang capture_id: ảnh lấy từ DB console, không đi ra mạng.
            image = asyncio.run_coroutine_threadsafe(self.store.crop(capture_id), loop).result(timeout=30)
            if image is None:
                raise ValueError("Ảnh đã bị xoá khỏi console")
            return image

        kwargs = {"fetch": fetch}
        if self._run is not None:
            kwargs["run"] = self._run
        try:
            rows = []
            for sample in samples:
                rows.append(await asyncio.to_thread(eval_service.evaluate_one, sample, **kwargs))
            summary = eval_service.summarize(rows)
            version = await asyncio.to_thread(self._engine_version)
            await self.store.finish_eval(run_id, "DONE", version, summary, None)
        except Exception as exc:  # noqa: BLE001 — lỗi phải hiện trên lượt đo, không chết lặng
            logger.warning("Console eval %s lỗi: %s", run_id, type(exc).__name__)
            await self.store.finish_eval(run_id, "FAILED", None, None, f"{type(exc).__name__}: {exc}")

    async def drain(self) -> None:
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)


model_lab_service = ModelLabService()
