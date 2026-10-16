"""Thành viên, vai trò và nhật ký của AI Console trong DB riêng `ai_console` (ADR-0048).

Mỗi thay đổi thành viên/vai trò ghi `audit_event` trong CÙNG transaction, để
không có thay đổi quyền nào mà thiếu dấu vết. `audit_event` bị trigger chặn
UPDATE/DELETE/TRUNCATE: sửa nhật ký là xoá bằng chứng.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable
from uuid import uuid4

from app.config import get_config
from app.core.exceptions import ConsoleStoreError


def _member(row) -> dict[str, Any]:
    return {
        "id": row[0], "email": row[1], "display_name": row[2], "status": row[3],
        "created_at": row[4].isoformat(), "roles": sorted(row[5] or []),
    }


_MEMBER_SELECT = """
    SELECT m.id::text, m.email, m.display_name, m.status, m.created_at,
           ARRAY_REMOVE(ARRAY_AGG(r.role), NULL)
    FROM console_member m
    LEFT JOIN console_member_role r ON r.member_id = m.id
"""


def _audit(cur, actor_id: str, action: str, target_type: str, target_id: str, reason: str) -> None:
    cur.execute(
        """INSERT INTO audit_event (id, actor_id, action, target_type, target_id, reason)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (str(uuid4()), actor_id, action, target_type, target_id, reason),
    )


class ConsoleStore:
    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or get_config().console.database_url
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    def _tx(self, work: Callable[[Any], Any]) -> Any:
        if not self.db_url:
            raise ConsoleStoreError("Thiếu AI_CONSOLE_DATABASE_URL cho AI Console.")
        try:
            import psycopg2

            connection = psycopg2.connect(self.db_url, connect_timeout=5)
            try:
                with connection:
                    with connection.cursor() as cursor:
                        return work(cursor)
            finally:
                connection.close()
        except (ConsoleStoreError, ValueError):
            raise
        except Exception as exc:
            raise ConsoleStoreError("Không truy cập được DB của AI Console.") from exc

    async def _run(self, work: Callable[[Any], Any]) -> Any:
        await self.ensure_schema()
        return await asyncio.to_thread(self._tx, work)

    @staticmethod
    def _create_schema(cur) -> None:
        cur.execute("SELECT pg_advisory_xact_lock(724201)")
        cur.execute(
            """CREATE TABLE IF NOT EXISTS console_member (
                id UUID PRIMARY KEY,
                email VARCHAR(254) NOT NULL,
                display_name VARCHAR(120) NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'INVITED',
                invited_by UUID,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT ck_console_member_status CHECK
                    (status IN ('INVITED', 'ACTIVE', 'DISABLED'))
            )"""
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_console_member_email "
            "ON console_member (LOWER(email))"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS console_member_role (
                member_id UUID NOT NULL REFERENCES console_member(id),
                role VARCHAR(32) NOT NULL,
                granted_by UUID,
                granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (member_id, role)
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS audit_event (
                id UUID PRIMARY KEY,
                actor_id UUID,
                action VARCHAR(64) NOT NULL,
                target_type VARCHAR(32) NOT NULL,
                target_id VARCHAR(100),
                reason TEXT NOT NULL,
                at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )"""
        )
        cur.execute(
            """CREATE OR REPLACE FUNCTION console_audit_append_only() RETURNS trigger AS $$
               BEGIN
                   RAISE EXCEPTION 'audit_event chỉ cho phép thêm mới';
               END;
               $$ LANGUAGE plpgsql"""
        )
        cur.execute(
            "CREATE OR REPLACE TRIGGER trg_audit_event_append_only "
            "BEFORE UPDATE OR DELETE ON audit_event "
            "FOR EACH ROW EXECUTE FUNCTION console_audit_append_only()"
        )
        cur.execute(
            "CREATE OR REPLACE TRIGGER trg_audit_event_no_truncate "
            "BEFORE TRUNCATE ON audit_event "
            "FOR EACH STATEMENT EXECUTE FUNCTION console_audit_append_only()"
        )

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            await asyncio.to_thread(self._tx, self._create_schema)
            self._schema_ready = True

    async def get_member(self, member_id: str) -> dict[str, Any] | None:
        def work(cur):
            cur.execute(_MEMBER_SELECT + " WHERE m.id = %s GROUP BY m.id", (member_id,))
            row = cur.fetchone()
            return _member(row) if row else None

        return await self._run(work)

    async def invite_member(
        self, email: str, display_name: str, actor_id: str, reason: str
    ) -> dict[str, Any]:
        def work(cur):
            cur.execute("SELECT 1 FROM console_member WHERE LOWER(email) = LOWER(%s)", (email,))
            if cur.fetchone():
                raise ConsoleStoreError("Email này đã được mời vào console.")
            member_id = str(uuid4())
            cur.execute(
                """INSERT INTO console_member (id, email, display_name, invited_by)
                   VALUES (%s, %s, %s, %s)""",
                (member_id, email, display_name, actor_id),
            )
            _audit(cur, actor_id, "member.invite", "member", member_id, reason)
            cur.execute(_MEMBER_SELECT + " WHERE m.id = %s GROUP BY m.id", (member_id,))
            return _member(cur.fetchone())

        return await self._run(work)

    async def grant_role(self, member_id: str, role: str, actor_id: str, reason: str) -> bool:
        """Trả False nếu thành viên đã có vai trò này (không ghi audit lần hai)."""
        def work(cur):
            cur.execute("SELECT 1 FROM console_member WHERE id = %s FOR UPDATE", (member_id,))
            if not cur.fetchone():
                raise ConsoleStoreError("Không tìm thấy thành viên console.")
            cur.execute(
                """INSERT INTO console_member_role (member_id, role, granted_by)
                   VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                (member_id, role, actor_id),
            )
            if cur.rowcount == 0:
                return False
            _audit(cur, actor_id, f"role.grant:{role}", "member", member_id, reason)
            return True

        return await self._run(work)

    async def revoke_role(self, member_id: str, role: str, actor_id: str, reason: str) -> bool:
        """Trả False nếu thành viên vốn không có vai trò này."""
        def work(cur):
            cur.execute(
                "DELETE FROM console_member_role WHERE member_id = %s AND role = %s",
                (member_id, role),
            )
            if cur.rowcount == 0:
                return False
            _audit(cur, actor_id, f"role.revoke:{role}", "member", member_id, reason)
            return True

        return await self._run(work)

    async def list_audit(self, limit: int) -> list[dict[str, Any]]:
        def work(cur):
            cur.execute(
                """SELECT id::text, actor_id::text, action, target_type, target_id, reason, at
                   FROM audit_event ORDER BY at DESC, id LIMIT %s""",
                (limit,),
            )
            return [
                {
                    "id": r[0], "actor_id": r[1] or "", "action": r[2], "target_type": r[3],
                    "target_id": r[4] or "", "reason": r[5], "at": r[6].isoformat(),
                }
                for r in cur.fetchall()
            ]

        return await self._run(work)


console_store = ConsoleStore()
