"""Dữ liệu vision của AI Console trong DB `ai_console` (IPLMS ADR-0048 §5, PROB-049 §5–§6).

- `vision_sample` + `vision_crop`: bản sao CHỈ ĐỌC từ backend qua kênh A2
  (`DatasetService.ExportForConsole`); không có session/user/area dạng rõ.
- `vision_label`: nhãn train chuyên sâu của console, provenance = console, duyệt
  bốn mắt ngay trên dòng nhãn.
- `vision_snapshot`, `model_version`, `eval_run`, `accept_policy`: P3–P5.

Mọi thao tác đổi trạng thái ghi `audit_event` trong CÙNG transaction.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.exceptions import ConsoleStoreError
from app.infra.database.console_store import ConsoleStore, _audit


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


_SAMPLE_COLUMNS = """
    s.capture_id::text, s.image_sha256, s.machine_plate, s.machine_confidence,
    s.confirmed_plate, s.human_corrected, s.selection_reasons, s.source_status, s.purpose,
    s.source_final_plate, s.group_ref, s.area_ref, s.captured_at, s.source_updated_at,
    s.imported_at
"""


def _sample(row) -> dict[str, Any]:
    return {
        "capture_id": row[0], "image_sha256": row[1], "machine_plate": row[2],
        "machine_confidence": row[3], "confirmed_plate": row[4], "human_corrected": row[5],
        "selection_reasons": list(row[6] or []), "source_status": row[7], "purpose": row[8],
        "source_final_plate": row[9] or "", "group_ref": row[10] or "", "area_ref": row[11] or "",
        "captured_at": _iso(row[12]), "source_updated_at": _iso(row[13]), "imported_at": _iso(row[14]),
    }


class ConsoleVisionStore(ConsoleStore):
    @staticmethod
    def _create_schema(cur) -> None:
        ConsoleStore._create_schema(cur)
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vision_sample (
                capture_id UUID PRIMARY KEY,
                image_sha256 CHAR(64) NOT NULL,
                machine_plate VARCHAR(20) NOT NULL DEFAULT '',
                machine_confidence DOUBLE PRECISION,
                confirmed_plate VARCHAR(20) NOT NULL DEFAULT '',
                human_corrected BOOLEAN NOT NULL DEFAULT FALSE,
                selection_reasons TEXT[] NOT NULL DEFAULT '{}',
                source_status VARCHAR(16) NOT NULL,
                purpose VARCHAR(8) NOT NULL DEFAULT 'train',
                source_final_plate VARCHAR(20),
                group_ref CHAR(64),
                area_ref CHAR(64),
                captured_at TIMESTAMPTZ,
                source_updated_at TIMESTAMPTZ NOT NULL,
                imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vision_crop (
                capture_id UUID PRIMARY KEY REFERENCES vision_sample(capture_id) ON DELETE CASCADE,
                image BYTEA NOT NULL
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vision_import_cursor (
                id SMALLINT PRIMARY KEY CHECK (id = 1),
                updated_at TIMESTAMPTZ NOT NULL,
                capture_id UUID NOT NULL
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vision_import_error (
                id UUID PRIMARY KEY,
                capture_id UUID NOT NULL,
                reason VARCHAR(200) NOT NULL,
                at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vision_label (
                id UUID PRIMARY KEY,
                capture_id UUID NOT NULL REFERENCES vision_sample(capture_id) ON DELETE CASCADE,
                labeler_id UUID NOT NULL REFERENCES console_member(id),
                verdict VARCHAR(16) NOT NULL,
                plate_text VARCHAR(20),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                decision VARCHAR(16),
                reviewer_id UUID REFERENCES console_member(id),
                review_note VARCHAR(500),
                reviewed_at TIMESTAMPTZ,
                CONSTRAINT ck_vision_label_verdict CHECK (verdict IN ('CORRECT', 'CORRECTED', 'UNUSABLE')),
                CONSTRAINT ck_vision_label_decision CHECK (decision IN ('APPROVED', 'REJECTED')),
                CONSTRAINT ck_vision_label_four_eyes CHECK (reviewer_id IS NULL OR reviewer_id <> labeler_id),
                CONSTRAINT uq_vision_label_capture_labeler UNIQUE (capture_id, labeler_id)
            )"""
        )
        # Một mẫu chỉ có một nhãn đang chờ duyệt và một nhãn đã duyệt.
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_vision_label_pending "
            "ON vision_label (capture_id) WHERE decision IS NULL"
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_vision_label_approved "
            "ON vision_label (capture_id) WHERE decision = 'APPROVED'"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vision_snapshot (
                id UUID PRIMARY KEY,
                kind VARCHAR(8) NOT NULL,
                name VARCHAR(120) NOT NULL,
                manifest JSONB NOT NULL,
                samples_sha256 CHAR(64) NOT NULL,
                sample_count INTEGER NOT NULL,
                created_by UUID NOT NULL REFERENCES console_member(id),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                frozen_by UUID REFERENCES console_member(id),
                frozen_at TIMESTAMPTZ,
                CONSTRAINT ck_vision_snapshot_kind CHECK (kind IN ('train', 'golden'))
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS model_version (
                id UUID PRIMARY KEY,
                name VARCHAR(64) NOT NULL,
                version VARCHAR(64) NOT NULL,
                artifact_key VARCHAR(500) NOT NULL,
                sha256 CHAR(64) NOT NULL,
                train_snapshot_id UUID REFERENCES vision_snapshot(id),
                stage VARCHAR(16) NOT NULL DEFAULT 'candidate',
                note VARCHAR(500) NOT NULL DEFAULT '',
                registered_by UUID NOT NULL REFERENCES console_member(id),
                registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                proposed_by UUID REFERENCES console_member(id),
                proposed_at TIMESTAMPTZ,
                approved_by UUID REFERENCES console_member(id),
                approved_at TIMESTAMPTZ,
                CONSTRAINT ck_model_version_stage CHECK
                    (stage IN ('candidate', 'proposed', 'production', 'retired')),
                CONSTRAINT ck_model_version_four_eyes CHECK (approved_by IS NULL OR approved_by <> proposed_by),
                CONSTRAINT uq_model_version UNIQUE (name, version)
            )"""
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_model_version_production "
            "ON model_version (name) WHERE stage = 'production'"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS eval_run (
                id UUID PRIMARY KEY,
                kind VARCHAR(16) NOT NULL DEFAULT 'anpr',
                snapshot_id UUID NOT NULL REFERENCES vision_snapshot(id),
                engine_version VARCHAR(120),
                metrics JSONB,
                status VARCHAR(16) NOT NULL DEFAULT 'RUNNING',
                error VARCHAR(500),
                started_by UUID NOT NULL REFERENCES console_member(id),
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMPTZ,
                CONSTRAINT ck_eval_run_status CHECK (status IN ('RUNNING', 'DONE', 'FAILED'))
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS accept_policy (
                id UUID PRIMARY KEY,
                model_name VARCHAR(64) NOT NULL,
                version INTEGER NOT NULL,
                auto_accept_threshold DOUBLE PRECISION NOT NULL,
                audit_rate DOUBLE PRECISION NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'PROPOSED',
                evidence JSONB NOT NULL DEFAULT '{}',
                reason VARCHAR(500) NOT NULL,
                proposed_by UUID NOT NULL REFERENCES console_member(id),
                proposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                decided_by UUID REFERENCES console_member(id),
                decided_at TIMESTAMPTZ,
                CONSTRAINT ck_accept_policy_status CHECK (status IN ('PROPOSED', 'APPROVED', 'REJECTED')),
                CONSTRAINT ck_accept_policy_four_eyes CHECK (decided_by IS NULL OR decided_by <> proposed_by),
                CONSTRAINT uq_accept_policy_version UNIQUE (model_name, version)
            )"""
        )

    # ── A2: nhập từ backend ──────────────────────────────────────────────────

    async def import_watermark(self) -> tuple[str, str] | None:
        def work(cur):
            cur.execute("SELECT updated_at, capture_id::text FROM vision_import_cursor WHERE id = 1")
            row = cur.fetchone()
            return (row[0].isoformat(), row[1]) if row else None

        return await self._run(work)

    async def existing_crops(self, capture_ids: list[str]) -> set[str]:
        """Mẫu đã có ảnh cùng sha256 thì không tải lại."""
        if not capture_ids:
            return set()

        def work(cur):
            cur.execute(
                """SELECT s.capture_id::text FROM vision_sample s
                   JOIN vision_crop c ON c.capture_id = s.capture_id
                   WHERE s.capture_id = ANY(%s::uuid[])""",
                (capture_ids,),
            )
            return {r[0] for r in cur.fetchall()}

        return await self._run(work)

    async def import_batch(
        self, samples: list[dict[str, Any]], crops: dict[str, bytes],
        rejects: list[tuple[str, str]], cursor: tuple[Any, str] | None, retention_days: int,
    ) -> None:
        """Ghi một lượt A2 nguyên tử: mẫu + ảnh + lỗi + con trỏ watermark."""
        def work(cur):
            for s in samples:
                cur.execute(
                    """INSERT INTO vision_sample
                       (capture_id, image_sha256, machine_plate, machine_confidence, confirmed_plate,
                        human_corrected, selection_reasons, source_status, purpose, source_final_plate,
                        group_ref, area_ref, captured_at, source_updated_at, expires_at)
                       VALUES (%(capture_id)s, %(image_sha256)s, %(machine_plate)s, %(machine_confidence)s,
                               %(confirmed_plate)s, %(human_corrected)s, %(selection_reasons)s,
                               %(status)s, %(purpose)s, %(final_plate)s, %(group_ref)s, %(area_ref)s,
                               %(captured_at)s, %(updated_at)s,
                               NOW() + make_interval(days => %(retention_days)s))
                       ON CONFLICT (capture_id) DO UPDATE SET
                           source_status = EXCLUDED.source_status,
                           purpose = EXCLUDED.purpose,
                           source_final_plate = EXCLUDED.source_final_plate,
                           source_updated_at = EXCLUDED.source_updated_at,
                           imported_at = NOW()""",
                    {**s, "retention_days": retention_days},
                )
                if s["capture_id"] in crops:
                    cur.execute(
                        """INSERT INTO vision_crop (capture_id, image) VALUES (%s, %s)
                           ON CONFLICT (capture_id) DO NOTHING""",
                        (s["capture_id"], crops[s["capture_id"]]),
                    )
            for capture_id, reason in rejects:
                cur.execute(
                    "INSERT INTO vision_import_error (id, capture_id, reason) VALUES (%s, %s, %s)",
                    (str(uuid4()), capture_id, reason[:200]),
                )
            if cursor is not None:
                cur.execute(
                    """INSERT INTO vision_import_cursor (id, updated_at, capture_id) VALUES (1, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET updated_at = EXCLUDED.updated_at,
                           capture_id = EXCLUDED.capture_id""",
                    cursor,
                )
            # Hết hạn và chưa có nhãn console, chưa vào snapshot nào → xoá (ảnh đi theo).
            cur.execute(
                """DELETE FROM vision_sample s WHERE s.expires_at < NOW()
                   AND NOT EXISTS (SELECT 1 FROM vision_label l WHERE l.capture_id = s.capture_id)"""
            )

        await self._run(work)

    async def import_status(self) -> dict[str, Any]:
        def work(cur):
            cur.execute("SELECT COUNT(*), MAX(imported_at) FROM vision_sample")
            total, last = cur.fetchone()
            cur.execute("SELECT updated_at FROM vision_import_cursor WHERE id = 1")
            row = cur.fetchone()
            cur.execute(
                "SELECT capture_id::text, reason, at FROM vision_import_error ORDER BY at DESC LIMIT 20"
            )
            errors = [{"capture_id": r[0], "reason": r[1], "at": r[2].isoformat()} for r in cur.fetchall()]
            return {
                "sample_count": int(total), "last_imported_at": _iso(last),
                "watermark_at": _iso(row[0]) if row else None, "recent_errors": errors,
            }

        return await self._run(work)

    # ── Gán nhãn và duyệt (P3) ──────────────────────────────────────────────

    async def label_queue(self, member_id: str, limit: int) -> list[dict[str, Any]]:
        """Mẫu chưa có nhãn chờ duyệt/đã duyệt mà người này chưa từng gán."""
        def work(cur):
            cur.execute(
                f"""SELECT {_SAMPLE_COLUMNS} FROM vision_sample s
                    WHERE s.source_status <> 'DISCARDED'
                      AND EXISTS (SELECT 1 FROM vision_crop c WHERE c.capture_id = s.capture_id)
                      AND NOT EXISTS (SELECT 1 FROM vision_label l WHERE l.capture_id = s.capture_id
                                      AND (l.decision IS NULL OR l.decision = 'APPROVED'))
                      AND NOT EXISTS (SELECT 1 FROM vision_label l WHERE l.capture_id = s.capture_id
                                      AND l.labeler_id = %s)
                    ORDER BY s.human_corrected DESC,
                             ('low_confidence' = ANY(s.selection_reasons)) DESC,
                             s.imported_at, s.capture_id
                    LIMIT %s""",
                (member_id, limit),
            )
            return [_sample(r) for r in cur.fetchall()]

        return await self._run(work)

    async def crop(self, capture_id: str) -> bytes | None:
        def work(cur):
            cur.execute("SELECT image FROM vision_crop WHERE capture_id = %s", (capture_id,))
            row = cur.fetchone()
            return bytes(row[0]) if row else None

        return await self._run(work)

    async def add_label(
        self, capture_id: str, labeler_id: str, verdict: str, plate_text: str | None
    ) -> str:
        def work(cur):
            cur.execute("SELECT 1 FROM vision_sample WHERE capture_id = %s FOR UPDATE", (capture_id,))
            if not cur.fetchone():
                raise ConsoleStoreError("Không tìm thấy mẫu này.")
            cur.execute(
                """SELECT labeler_id::text, decision FROM vision_label WHERE capture_id = %s
                   AND (decision IS NULL OR decision = 'APPROVED' OR labeler_id = %s)""",
                (capture_id, labeler_id),
            )
            for other, decision in cur.fetchall():
                if other == labeler_id:
                    raise ConsoleStoreError("Bạn đã gán nhãn mẫu này.")
                raise ConsoleStoreError(
                    "Mẫu đã có nhãn đang chờ duyệt." if decision is None else "Mẫu đã có nhãn được duyệt."
                )
            label_id = str(uuid4())
            cur.execute(
                """INSERT INTO vision_label (id, capture_id, labeler_id, verdict, plate_text)
                   VALUES (%s, %s, %s, %s, %s)""",
                (label_id, capture_id, labeler_id, verdict, plate_text),
            )
            _audit(cur, labeler_id, f"vision.label:{verdict}", "vision_sample", capture_id, "gán nhãn")
            return label_id

        return await self._run(work)

    async def review_queue(self, member_id: str, limit: int) -> list[dict[str, Any]]:
        """Nhãn chờ duyệt của NGƯỜI KHÁC — người gán không thấy nhãn của mình ở đây."""
        def work(cur):
            cur.execute(
                f"""SELECT {_SAMPLE_COLUMNS}, l.id::text, l.verdict, l.plate_text, m.display_name, l.created_at
                    FROM vision_label l
                    JOIN vision_sample s ON s.capture_id = l.capture_id
                    JOIN console_member m ON m.id = l.labeler_id
                    WHERE l.decision IS NULL AND l.labeler_id <> %s
                    ORDER BY l.created_at, l.id LIMIT %s""",
                (member_id, limit),
            )
            return [
                {**_sample(r), "label": {"id": r[15], "verdict": r[16], "plate_text": r[17] or "",
                                         "labeler": r[18], "created_at": r[19].isoformat()}}
                for r in cur.fetchall()
            ]

        return await self._run(work)

    async def decide_label(self, label_id: str, reviewer_id: str, decision: str, note: str) -> None:
        def work(cur):
            cur.execute(
                "SELECT labeler_id::text, decision FROM vision_label WHERE id = %s FOR UPDATE",
                (label_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ConsoleStoreError("Không tìm thấy nhãn này.")
            labeler_id, current = row
            if current is not None:
                raise ConsoleStoreError("Nhãn này đã được duyệt rồi.")
            if labeler_id == reviewer_id:
                raise ConsoleStoreError("Không được tự duyệt nhãn của mình.")
            cur.execute(
                """UPDATE vision_label SET decision = %s, reviewer_id = %s, review_note = %s,
                       reviewed_at = NOW() WHERE id = %s""",
                (decision, reviewer_id, note, label_id),
            )
            _audit(cur, reviewer_id, f"vision.review:{decision}", "vision_label", label_id,
                   note or f"duyệt {decision}")

        await self._run(work)

    async def approved_samples(self) -> list[dict[str, Any]]:
        """Mẫu có nhãn console đã duyệt (nguồn cho snapshot)."""
        def work(cur):
            cur.execute(
                """SELECT s.capture_id::text, s.image_sha256, s.group_ref, l.verdict, l.plate_text,
                          s.confirmed_plate
                   FROM vision_label l JOIN vision_sample s ON s.capture_id = l.capture_id
                   WHERE l.decision = 'APPROVED' ORDER BY s.capture_id"""
            )
            return [
                {"capture_id": r[0], "sha256": r[1], "group_ref": r[2] or r[0], "verdict": r[3],
                 "plate_text": r[4] or "", "confirmed_plate": r[5]}
                for r in cur.fetchall()
            ]

        return await self._run(work)

    async def label_counts(self) -> dict[str, int]:
        def work(cur):
            cur.execute(
                """SELECT
                       (SELECT COUNT(*) FROM vision_sample),
                       (SELECT COUNT(*) FROM vision_label WHERE decision IS NULL),
                       (SELECT COUNT(*) FROM vision_label WHERE decision = 'APPROVED'),
                       (SELECT COUNT(*) FROM vision_label WHERE decision = 'REJECTED')"""
            )
            total, pending, approved, rejected = cur.fetchone()
            return {"samples": int(total), "pending_review": int(pending),
                    "approved": int(approved), "rejected": int(rejected)}

        return await self._run(work)

    # ── Snapshot ────────────────────────────────────────────────────────────

    async def create_snapshot(
        self, kind: str, name: str, lock: dict[str, Any], actor_id: str
    ) -> str:
        def work(cur):
            snapshot_id = str(uuid4())
            cur.execute(
                """INSERT INTO vision_snapshot (id, kind, name, manifest, samples_sha256, sample_count, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (snapshot_id, kind, name, json.dumps(lock, ensure_ascii=False), lock["samples_sha256"],
                 lock["sample_count"], actor_id),
            )
            _audit(cur, actor_id, f"snapshot.create:{kind}", "vision_snapshot", snapshot_id, name)
            return snapshot_id

        return await self._run(work)

    async def frozen_golden_groups(self) -> set[str]:
        def work(cur):
            cur.execute(
                """SELECT DISTINCT e->>'group_id' FROM vision_snapshot,
                       jsonb_array_elements(manifest->'samples') e
                   WHERE kind = 'golden' AND frozen_at IS NOT NULL"""
            )
            return {r[0] for r in cur.fetchall() if r[0]}

        return await self._run(work)

    async def freeze_snapshot(self, snapshot_id: str, actor_id: str, reason: str) -> None:
        def work(cur):
            cur.execute(
                "SELECT kind, frozen_at FROM vision_snapshot WHERE id = %s FOR UPDATE", (snapshot_id,)
            )
            row = cur.fetchone()
            if not row:
                raise ConsoleStoreError("Không tìm thấy snapshot.")
            if row[0] != "golden":
                raise ConsoleStoreError("Chỉ khoá được snapshot golden.")
            if row[1] is not None:
                raise ConsoleStoreError("Snapshot đã khoá.")
            cur.execute(
                "UPDATE vision_snapshot SET frozen_by = %s, frozen_at = NOW() WHERE id = %s",
                (actor_id, snapshot_id),
            )
            _audit(cur, actor_id, "snapshot.freeze", "vision_snapshot", snapshot_id, reason)

        await self._run(work)

    async def list_snapshots(self) -> list[dict[str, Any]]:
        def work(cur):
            cur.execute(
                """SELECT v.id::text, v.kind, v.name, v.samples_sha256, v.sample_count, c.display_name,
                          v.created_at, f.display_name, v.frozen_at
                   FROM vision_snapshot v JOIN console_member c ON c.id = v.created_by
                   LEFT JOIN console_member f ON f.id = v.frozen_by
                   ORDER BY v.created_at DESC"""
            )
            return [
                {"id": r[0], "kind": r[1], "name": r[2], "samples_sha256": r[3], "sample_count": r[4],
                 "created_by": r[5], "created_at": r[6].isoformat(), "frozen_by": r[7] or "",
                 "frozen_at": _iso(r[8])}
                for r in cur.fetchall()
            ]

        return await self._run(work)

    async def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        def work(cur):
            cur.execute(
                "SELECT id::text, kind, manifest, frozen_at FROM vision_snapshot WHERE id = %s",
                (snapshot_id,),
            )
            r = cur.fetchone()
            return {"id": r[0], "kind": r[1], "manifest": r[2], "frozen_at": _iso(r[3])} if r else None

        return await self._run(work)

    # ── Model + eval (P4) ───────────────────────────────────────────────────

    async def register_model(self, data: dict[str, Any], actor_id: str) -> str:
        def work(cur):
            model_id = str(uuid4())
            cur.execute("SELECT 1 FROM model_version WHERE name = %s AND version = %s",
                        (data["name"], data["version"]))
            if cur.fetchone():
                raise ConsoleStoreError("Đã có model với tên và phiên bản này.")
            cur.execute(
                """INSERT INTO model_version (id, name, version, artifact_key, sha256, train_snapshot_id,
                       note, registered_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (model_id, data["name"], data["version"], data["artifact_key"], data["sha256"],
                 data.get("train_snapshot_id"), data.get("note", ""), actor_id),
            )
            _audit(cur, actor_id, "model.register", "model_version", model_id,
                   f"{data['name']}@{data['version']}")
            return model_id

        return await self._run(work)

    async def get_model(self, model_id: str) -> dict[str, Any] | None:
        rows = await self.list_models(model_id)
        return rows[0] if rows else None

    async def list_models(self, model_id: str | None = None) -> list[dict[str, Any]]:
        def work(cur):
            cur.execute(
                """SELECT m.id::text, m.name, m.version, m.artifact_key, m.sha256,
                          m.train_snapshot_id::text, m.stage, m.note, r.display_name, m.registered_at,
                          m.proposed_by::text, p.display_name, m.proposed_at, a.display_name, m.approved_at
                   FROM model_version m JOIN console_member r ON r.id = m.registered_by
                   LEFT JOIN console_member p ON p.id = m.proposed_by
                   LEFT JOIN console_member a ON a.id = m.approved_by
                   WHERE %s::uuid IS NULL OR m.id = %s::uuid
                   ORDER BY m.registered_at DESC""",
                (model_id, model_id),
            )
            return [
                {"id": r[0], "name": r[1], "version": r[2], "artifact_key": r[3], "sha256": r[4],
                 "train_snapshot_id": r[5] or "", "stage": r[6], "note": r[7], "registered_by": r[8],
                 "registered_at": r[9].isoformat(), "proposed_by_id": r[10] or "",
                 "proposed_by": r[11] or "", "proposed_at": _iso(r[12]), "approved_by": r[13] or "",
                 "approved_at": _iso(r[14])}
                for r in cur.fetchall()
            ]

        return await self._run(work)

    async def propose_model(self, model_id: str, actor_id: str, reason: str) -> None:
        def work(cur):
            cur.execute("SELECT stage FROM model_version WHERE id = %s FOR UPDATE", (model_id,))
            row = cur.fetchone()
            if not row:
                raise ConsoleStoreError("Không tìm thấy model.")
            if row[0] != "candidate":
                raise ConsoleStoreError("Chỉ đề xuất được model đang ở trạng thái candidate.")
            cur.execute(
                """UPDATE model_version SET stage = 'proposed', proposed_by = %s, proposed_at = NOW()
                   WHERE id = %s""",
                (actor_id, model_id),
            )
            _audit(cur, actor_id, "model.propose", "model_version", model_id, reason)

        await self._run(work)

    async def promote_model(self, model_id: str, actor_id: str, reason: str) -> None:
        def work(cur):
            cur.execute(
                "SELECT name, stage, proposed_by::text FROM model_version WHERE id = %s FOR UPDATE",
                (model_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ConsoleStoreError("Không tìm thấy model.")
            name, stage, proposed_by = row
            if stage != "proposed":
                raise ConsoleStoreError("Model phải được đề xuất trước khi promote.")
            if proposed_by == actor_id:
                raise ConsoleStoreError("Người đề xuất không được tự promote.")
            cur.execute(
                """UPDATE model_version SET stage = 'retired'
                   WHERE name = %s AND stage = 'production' RETURNING id::text""",
                (name,),
            )
            for (retired_id,) in cur.fetchall():
                _audit(cur, actor_id, "model.retire", "model_version", retired_id, f"thay bởi {model_id}")
            cur.execute(
                """UPDATE model_version SET stage = 'production', approved_by = %s, approved_at = NOW()
                   WHERE id = %s""",
                (actor_id, model_id),
            )
            _audit(cur, actor_id, "model.promote", "model_version", model_id, reason)

        await self._run(work)

    async def start_eval(self, snapshot_id: str, actor_id: str) -> str:
        def work(cur):
            run_id = str(uuid4())
            cur.execute(
                "INSERT INTO eval_run (id, snapshot_id, started_by) VALUES (%s, %s, %s)",
                (run_id, snapshot_id, actor_id),
            )
            _audit(cur, actor_id, "eval.start", "eval_run", run_id, f"snapshot {snapshot_id}")
            return run_id

        return await self._run(work)

    async def finish_eval(
        self, run_id: str, status: str, engine_version: str | None,
        metrics: dict[str, Any] | None, error: str | None,
    ) -> None:
        def work(cur):
            cur.execute(
                """UPDATE eval_run SET status = %s, engine_version = %s, metrics = %s, error = %s,
                       finished_at = NOW() WHERE id = %s AND status = 'RUNNING'""",
                (status, engine_version, json.dumps(metrics) if metrics is not None else None,
                 (error or "")[:500] or None, run_id),
            )

        await self._run(work)

    async def list_evals(self, limit: int = 50) -> list[dict[str, Any]]:
        def work(cur):
            cur.execute(
                """SELECT e.id::text, e.kind, e.snapshot_id::text, v.name, e.engine_version, e.metrics,
                          e.status, e.error, m.display_name, e.started_at, e.finished_at
                   FROM eval_run e JOIN vision_snapshot v ON v.id = e.snapshot_id
                   JOIN console_member m ON m.id = e.started_by
                   ORDER BY e.started_at DESC LIMIT %s""",
                (limit,),
            )
            return [
                {"id": r[0], "kind": r[1], "snapshot_id": r[2], "snapshot_name": r[3],
                 "engine_version": r[4] or "", "metrics": r[5], "status": r[6], "error": r[7] or "",
                 "started_by": r[8], "started_at": r[9].isoformat(), "finished_at": _iso(r[10])}
                for r in cur.fetchall()
            ]

        return await self._run(work)

    async def evals_for_engine_digest(self, digest: str) -> list[dict[str, Any]]:
        """Lượt đo xong trên golden ĐÃ KHOÁ mà engine có weights khớp `digest` (12 ký tự đầu sha256)."""
        def work(cur):
            cur.execute(
                """SELECT e.id::text FROM eval_run e JOIN vision_snapshot v ON v.id = e.snapshot_id
                   WHERE e.status = 'DONE' AND v.kind = 'golden' AND v.frozen_at IS NOT NULL
                     AND e.engine_version LIKE %s""",
                (f"yolo:{digest}+%",),
            )
            return [{"id": r[0]} for r in cur.fetchall()]

        return await self._run(work)

    # ── Accept policy + độ chính xác thật (P5) ──────────────────────────────

    async def audit_samples(self) -> list[dict[str, Any]]:
        """Mẫu bốc ngẫu nhiên (random_audit) đã có nhãn người: nhãn console đã duyệt ưu tiên,
        không có thì dùng nhãn moderator đã chốt ở backend."""
        def work(cur):
            cur.execute(
                """SELECT s.capture_id::text, s.machine_plate, s.machine_confidence,
                          CASE WHEN l.verdict = 'CORRECT' THEN s.confirmed_plate ELSE l.plate_text END,
                          l.verdict, s.source_final_plate, s.source_status
                   FROM vision_sample s
                   LEFT JOIN vision_label l ON l.capture_id = s.capture_id AND l.decision = 'APPROVED'
                   WHERE 'random_audit' = ANY(s.selection_reasons)
                     AND s.machine_confidence IS NOT NULL
                     AND (l.id IS NOT NULL OR s.source_final_plate IS NOT NULL)
                     AND COALESCE(l.verdict, '') <> 'UNUSABLE'
                     AND s.source_status <> 'DISCARDED'
                   ORDER BY s.capture_id"""
            )
            rows = []
            for cid, machine, conf, console_truth, verdict, backend_truth, _ in cur.fetchall():
                truth = console_truth if verdict else backend_truth
                rows.append({"capture_id": cid, "machine_plate": machine, "confidence": float(conf),
                             "truth": truth or "", "truth_source": "console" if verdict else "moderator"})
            return rows

        return await self._run(work)

    async def propose_policy(
        self, model_name: str, threshold: float, audit_rate: float, evidence: dict[str, Any],
        reason: str, actor_id: str,
    ) -> dict[str, Any]:
        def work(cur):
            cur.execute("SELECT pg_advisory_xact_lock(724202)")
            cur.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM accept_policy WHERE model_name = %s",
                        (model_name,))
            version = int(cur.fetchone()[0])
            policy_id = str(uuid4())
            cur.execute(
                """INSERT INTO accept_policy (id, model_name, version, auto_accept_threshold, audit_rate,
                       evidence, reason, proposed_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (policy_id, model_name, version, threshold, audit_rate, json.dumps(evidence), reason, actor_id),
            )
            _audit(cur, actor_id, "policy.propose", "accept_policy", policy_id, reason)
            return {"id": policy_id, "version": version}

        return await self._run(work)

    async def decide_policy(self, policy_id: str, actor_id: str, decision: str, reason: str) -> None:
        def work(cur):
            cur.execute(
                "SELECT status, proposed_by::text FROM accept_policy WHERE id = %s FOR UPDATE", (policy_id,)
            )
            row = cur.fetchone()
            if not row:
                raise ConsoleStoreError("Không tìm thấy đề xuất ngưỡng.")
            if row[0] != "PROPOSED":
                raise ConsoleStoreError("Đề xuất này đã được quyết.")
            if row[1] == actor_id:
                raise ConsoleStoreError("Người đề xuất không được tự duyệt ngưỡng.")
            cur.execute(
                """UPDATE accept_policy SET status = %s, decided_by = %s, decided_at = NOW() WHERE id = %s""",
                (decision, actor_id, policy_id),
            )
            _audit(cur, actor_id, f"policy.{decision.lower()}", "accept_policy", policy_id, reason)

        await self._run(work)

    async def list_policies(self) -> list[dict[str, Any]]:
        def work(cur):
            cur.execute(
                """SELECT a.id::text, a.model_name, a.version, a.auto_accept_threshold, a.audit_rate,
                          a.status, a.evidence, a.reason, p.display_name, a.proposed_at,
                          d.display_name, a.decided_at, a.proposed_by::text
                   FROM accept_policy a JOIN console_member p ON p.id = a.proposed_by
                   LEFT JOIN console_member d ON d.id = a.decided_by
                   ORDER BY a.model_name, a.version DESC"""
            )
            return [
                {"id": r[0], "model_name": r[1], "version": r[2], "auto_accept_threshold": r[3],
                 "audit_rate": r[4], "status": r[5], "evidence": r[6], "reason": r[7],
                 "proposed_by": r[8], "proposed_at": r[9].isoformat(), "decided_by": r[10] or "",
                 "decided_at": _iso(r[11]), "proposed_by_id": r[12]}
                for r in cur.fetchall()
            ]

        return await self._run(work)


console_vision_store = ConsoleVisionStore()
