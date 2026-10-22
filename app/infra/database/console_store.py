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
from app.core.exceptions import ConsoleAuthError, ConsoleStoreError


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

            try:
                connection = psycopg2.connect(self.db_url, connect_timeout=3)
            except Exception:
                for old in ("@ai-db:5432/", "@127.0.0.1:5432/", "@localhost:5432/"):
                    if old in self.db_url:
                        fallback_url = self.db_url.replace(old, "@127.0.0.1:5435/")
                        try:
                            connection = psycopg2.connect(fallback_url, connect_timeout=3)
                            self.db_url = fallback_url
                            break
                        except Exception:
                            pass
                else:
                    raise
            try:
                with connection:
                    with connection.cursor() as cursor:
                        return work(cursor)
            finally:
                connection.close()
        except (ConsoleAuthError, ConsoleStoreError, ValueError):
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
        # ── Đăng nhập (P1b) ──
        for column in (
            "google_sub VARCHAR(255)", "password_hash TEXT", "totp_secret_enc TEXT",
            "totp_enabled_at TIMESTAMPTZ", "totp_last_step BIGINT",
            "password_failures INT NOT NULL DEFAULT 0", "password_locked_until TIMESTAMPTZ",
        ):
            cur.execute(f"ALTER TABLE console_member ADD COLUMN IF NOT EXISTS {column}")
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_console_member_google_sub "
            "ON console_member (google_sub) WHERE google_sub IS NOT NULL"
        )
        # ── Chấm lượt trả lời Copilot (P1c) — lượt nằm ở database-vector, chỉ giữ turn_id + thời điểm ──
        cur.execute(
            """CREATE TABLE IF NOT EXISTS copilot_turn_review (
                turn_id UUID PRIMARY KEY,
                turn_at TIMESTAMPTZ NOT NULL,
                verdict VARCHAR(16) NOT NULL,
                note VARCHAR(500) NOT NULL DEFAULT '',
                reviewer_id UUID NOT NULL REFERENCES console_member(id),
                reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT ck_copilot_turn_review_verdict CHECK
                    (verdict IN ('CORRECT', 'INCORRECT', 'UNSAFE'))
            )"""
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_copilot_turn_review_turn_at ON copilot_turn_review (turn_at)"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS console_session (
                id UUID PRIMARY KEY,
                token_hash CHAR(64) NOT NULL UNIQUE,
                member_id UUID NOT NULL REFERENCES console_member(id),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                mfa_at TIMESTAMPTZ,
                step_up_at TIMESTAMPTZ,
                revoked_at TIMESTAMPTZ
            )"""
        )
        cur.execute(
            "ALTER TABLE console_session ADD COLUMN IF NOT EXISTS totp_failures INT NOT NULL DEFAULT 0"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS console_auth_flow (
                state_hash CHAR(64) PRIMARY KEY,
                browser_hash CHAR(64) NOT NULL,
                nonce VARCHAR(128) NOT NULL,
                code_verifier VARCHAR(128) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )"""
        )

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            try:
                await asyncio.to_thread(self._tx, self._create_schema)
            except Exception as exc:
                # IPLMS ADR-0051: Khi process inference dùng user bị siết quyền (ai_inference),
                # bỏ qua lỗi permission denied nếu các bảng đã được console_main khởi tạo từ trước.
                if "permission denied" in str(exc).lower():
                    pass
                else:
                    raise
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

    async def add_audit(self, actor_id: str, action: str, target_type: str, target_id: str, reason: str) -> None:
        """Thao tác ghi ra ngoài DB console (vd. nạp tri thức vào database-vector) vẫn để dấu vết ở đây."""
        await self._run(lambda cur: _audit(cur, actor_id, action, target_type, target_id, reason))

    async def list_members(self) -> list[dict[str, Any]]:
        def work(cur):
            cur.execute(_MEMBER_SELECT + " GROUP BY m.id ORDER BY m.created_at, m.id")
            return [_member(r) for r in cur.fetchall()]

        return await self._run(work)

    # ── Chấm lượt Copilot (P1c) ──────────────────────────────────────────────

    async def review_turn(
        self, turn_id: str, turn_at, verdict: str, note: str, actor_id: str
    ) -> None:
        """Chấm lại thì ghi đè kết quả cũ; mỗi lần chấm đều có một dòng audit."""
        def work(cur):
            cur.execute(
                """INSERT INTO copilot_turn_review (turn_id, turn_at, verdict, note, reviewer_id)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (turn_id) DO UPDATE SET verdict = EXCLUDED.verdict,
                       note = EXCLUDED.note, reviewer_id = EXCLUDED.reviewer_id,
                       reviewed_at = NOW()""",
                (turn_id, turn_at, verdict, note, actor_id),
            )
            _audit(cur, actor_id, f"copilot.review:{verdict}", "copilot_turn", turn_id,
                   note or f"chấm {verdict}")

        await self._run(work)

    async def get_reviews(self, turn_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not turn_ids:
            return {}

        def work(cur):
            cur.execute(
                """SELECT r.turn_id::text, r.verdict, r.note, m.display_name, r.reviewed_at
                   FROM copilot_turn_review r JOIN console_member m ON m.id = r.reviewer_id
                   WHERE r.turn_id = ANY(%s::uuid[])""",
                (turn_ids,),
            )
            return {
                r[0]: {"verdict": r[1], "note": r[2], "reviewer": r[3],
                       "reviewed_at": r[4].isoformat()}
                for r in cur.fetchall()
            }

        return await self._run(work)

    async def review_stats(self, days: int) -> dict[str, int]:
        def work(cur):
            cur.execute(
                """SELECT verdict, COUNT(*) FROM copilot_turn_review
                   WHERE turn_at >= NOW() - make_interval(days => %s) GROUP BY verdict""",
                (days,),
            )
            return {verdict: int(n) for verdict, n in cur.fetchall()}

        return await self._run(work)

    # ── Đăng nhập (P1b) ──────────────────────────────────────────────────────

    async def create_auth_flow(
        self, state_hash: str, browser_hash: str, nonce: str, code_verifier: str
    ) -> None:
        def work(cur):
            cur.execute(
                "DELETE FROM console_auth_flow WHERE created_at < NOW() - INTERVAL '10 minutes'"
            )
            cur.execute(
                """INSERT INTO console_auth_flow (state_hash, browser_hash, nonce, code_verifier)
                   VALUES (%s, %s, %s, %s)""",
                (state_hash, browser_hash, nonce, code_verifier),
            )

        await self._run(work)

    async def consume_auth_flow(self, state_hash: str, browser_hash: str) -> dict[str, str] | None:
        """Dùng một lần: xoá luôn khi đọc; quá 10 phút hoặc khác trình duyệt → None."""
        def work(cur):
            cur.execute(
                """DELETE FROM console_auth_flow
                   WHERE state_hash = %s AND browser_hash = %s
                     AND created_at > NOW() - INTERVAL '10 minutes'
                   RETURNING nonce, code_verifier""",
                (state_hash, browser_hash),
            )
            row = cur.fetchone()
            return {"nonce": row[0], "code_verifier": row[1]} if row else None

        return await self._run(work)

    async def get_login_member(self, email: str) -> dict[str, Any] | None:
        def work(cur):
            cur.execute(
                """SELECT id::text, status, google_sub, password_hash, totp_secret_enc,
                          totp_enabled_at IS NOT NULL,
                          COALESCE(password_locked_until > NOW(), FALSE)
                   FROM console_member WHERE LOWER(email) = LOWER(%s)""",
                (email,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0], "status": row[1], "google_sub": row[2],
                "password_hash": row[3], "totp_secret_enc": row[4], "totp_enabled": row[5],
                "password_locked": row[6],
            }

        return await self._run(work)

    async def open_session(
        self, member_id: str, token_hash: str, method: str, google_sub: str | None = None
    ) -> str:
        """Gắn google_sub lần đầu (sau đó phải khớp), tạo phiên chưa qua MFA, ghi audit."""
        def work(cur):
            if google_sub is not None:
                cur.execute(
                    """UPDATE console_member SET google_sub = %s
                       WHERE id = %s AND (google_sub IS NULL OR google_sub = %s)
                       RETURNING id""",
                    (google_sub, member_id, google_sub),
                )
                if not cur.fetchone():
                    raise ConsoleAuthError("Tài khoản Google không khớp thành viên đã đăng ký.")
            if method == "password":
                cur.execute(
                    "UPDATE console_member SET password_failures = 0, password_locked_until = NULL "
                    "WHERE id = %s",
                    (member_id,),
                )
            session_id = str(uuid4())
            cur.execute(
                "INSERT INTO console_session (id, token_hash, member_id) VALUES (%s, %s, %s)",
                (session_id, token_hash, member_id),
            )
            _audit(cur, member_id, f"auth.login:{method}", "session", session_id, "đăng nhập")
            return session_id

        return await self._run(work)

    async def get_session(self, token_hash: str) -> dict[str, Any] | None:
        def work(cur):
            cur.execute(
                """SELECT s.id::text, s.created_at, s.last_seen_at, s.mfa_at, s.step_up_at,
                          s.revoked_at, m.id::text, m.email, m.display_name, m.status,
                          m.totp_secret_enc, m.totp_enabled_at IS NOT NULL,
                          ARRAY_REMOVE(ARRAY_AGG(r.role), NULL)
                   FROM console_session s
                   JOIN console_member m ON m.id = s.member_id
                   LEFT JOIN console_member_role r ON r.member_id = m.id
                   WHERE s.token_hash = %s
                   GROUP BY s.id, m.id""",
                (token_hash,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "session_id": row[0], "created_at": row[1], "last_seen_at": row[2],
                "mfa_at": row[3], "step_up_at": row[4], "revoked_at": row[5],
                "member_id": row[6], "email": row[7], "display_name": row[8],
                "member_status": row[9], "totp_secret_enc": row[10], "totp_enabled": row[11],
                "roles": sorted(row[12] or []),
            }

        return await self._run(work)

    async def touch_session(self, session_id: str) -> None:
        def work(cur):
            cur.execute("UPDATE console_session SET last_seen_at = NOW() WHERE id = %s", (session_id,))

        await self._run(work)

    async def set_totp_secret(self, member_id: str, secret_enc: str) -> None:
        """Chỉ đặt khi TOTP chưa bật — bật rồi thì không cho đăng ký lại qua đường này."""
        def work(cur):
            cur.execute(
                """UPDATE console_member SET totp_secret_enc = %s
                   WHERE id = %s AND totp_enabled_at IS NULL RETURNING id""",
                (secret_enc, member_id),
            )
            if not cur.fetchone():
                raise ConsoleAuthError("TOTP đã được bật cho tài khoản này.", "TOTP_ALREADY_ENROLLED")

        await self._run(work)

    async def accept_totp(
        self, member_id: str, session_id: str, step: int, step_up_reason: str | None = None
    ) -> None:
        """Tiêu một time-step TOTP (chống dùng lại mã), rồi đánh dấu MFA hoặc step-up."""
        def work(cur):
            cur.execute(
                """UPDATE console_member
                   SET totp_last_step = %s,
                       totp_enabled_at = COALESCE(totp_enabled_at, NOW()),
                       status = CASE WHEN status = 'INVITED' THEN 'ACTIVE' ELSE status END
                   WHERE id = %s AND status <> 'DISABLED'
                     AND COALESCE(totp_last_step, -1) < %s
                   RETURNING id""",
                (step, member_id, step),
            )
            if not cur.fetchone():
                raise ConsoleAuthError("Mã xác thực đã được dùng hoặc tài khoản bị khoá.", "TOTP_INVALID")
            if step_up_reason is None:
                cur.execute("UPDATE console_session SET mfa_at = NOW() WHERE id = %s", (session_id,))
                _audit(cur, member_id, "auth.mfa", "session", session_id, "xác thực TOTP")
            else:
                cur.execute("UPDATE console_session SET step_up_at = NOW() WHERE id = %s", (session_id,))
                _audit(cur, member_id, "auth.step_up", "session", session_id, step_up_reason)

        await self._run(work)

    async def fail_password(self, member_id: str, max_failures: int, lock_minutes: int) -> None:
        """Đếm lần sai mật khẩu; tới ngưỡng thì khoá đăng nhập mật khẩu một lúc và ghi audit."""
        def work(cur):
            cur.execute(
                """UPDATE console_member
                   SET password_failures = password_failures + 1,
                       password_locked_until = CASE WHEN password_failures + 1 >= %s
                           THEN NOW() + make_interval(mins => %s) ELSE password_locked_until END
                   WHERE id = %s RETURNING password_failures""",
                (max_failures, lock_minutes, member_id),
            )
            row = cur.fetchone()
            if row and row[0] >= max_failures:
                cur.execute("UPDATE console_member SET password_failures = 0 WHERE id = %s", (member_id,))
                _audit(cur, member_id, "auth.password_locked", "member", member_id,
                       f"sai mật khẩu {max_failures} lần")

        await self._run(work)

    async def fail_totp(self, session_id: str, member_id: str, max_failures: int) -> bool:
        """Đếm lần sai TOTP trong phiên; tới ngưỡng thì thu hồi phiên. Trả True nếu đã thu hồi."""
        def work(cur):
            cur.execute(
                """UPDATE console_session
                   SET totp_failures = totp_failures + 1,
                       revoked_at = CASE WHEN totp_failures + 1 >= %s
                           THEN COALESCE(revoked_at, NOW()) ELSE revoked_at END
                   WHERE id = %s RETURNING totp_failures""",
                (max_failures, session_id),
            )
            row = cur.fetchone()
            revoked = bool(row and row[0] >= max_failures)
            if revoked:
                _audit(cur, member_id, "auth.totp_locked", "session", session_id,
                       f"sai TOTP {max_failures} lần")
            return revoked

        return await self._run(work)

    async def revoke_session(self, session_id: str, member_id: str) -> None:
        def work(cur):
            cur.execute(
                "UPDATE console_session SET revoked_at = NOW() WHERE id = %s AND revoked_at IS NULL",
                (session_id,),
            )
            if cur.rowcount:
                _audit(cur, member_id, "auth.logout", "session", session_id, "đăng xuất")

        await self._run(work)

    async def create_emergency_admin(
        self, email: str, display_name: str, password_hash: str, totp_secret_enc: str, role: str
    ) -> str:
        """Tài khoản admin khẩn cấp tạo bằng CLI trên AI host (ADR-0048 §4)."""
        def work(cur):
            cur.execute("SELECT 1 FROM console_member WHERE LOWER(email) = LOWER(%s)", (email,))
            if cur.fetchone():
                raise ConsoleStoreError("Email này đã có trong console.")
            member_id = str(uuid4())
            cur.execute(
                """INSERT INTO console_member (id, email, display_name, password_hash, totp_secret_enc)
                   VALUES (%s, %s, %s, %s, %s)""",
                (member_id, email, display_name, password_hash, totp_secret_enc),
            )
            cur.execute(
                "INSERT INTO console_member_role (member_id, role) VALUES (%s, %s)",
                (member_id, role),
            )
            _audit(cur, None, "system.bootstrap_admin", "member", member_id, "tạo bằng CLI trên AI host")
            return member_id

        return await self._run(work)


console_store = ConsoleStore()
