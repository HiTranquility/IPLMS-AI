"""Đăng nhập AI Console: Google/mật khẩu khẩn cấp → TOTP → phiên → step-up (ADR-0048 §4).

Token phiên chỉ nằm trong cookie của trình duyệt; DB giữ SHA-256 của nó, nên
đọc được DB cũng không mượn được phiên.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.config import get_config
from app.core.console.dtos import ConsoleActor, ConsoleSession
from app.core.console.engines import access_policy, session_policy
from app.core.exceptions import ConsoleAccessDenied, ConsoleAuthError
from app.util.logger import logger
from app.infra.database.console_store import console_store
from app.infra.identity.google_oidc import GoogleOidcClient, new_pkce_pair
from app.infra.identity.password import verify_password
from app.infra.identity.totp import TotpVault

_LOGIN_FAILED = "Email hoặc mật khẩu không đúng."
# Chặn dò mã: TOTP 6 số, mật khẩu khẩn cấp — console chỉ nội bộ nhưng vẫn không cho thử vô hạn.
MAX_AUTH_FAILURES = 5
PASSWORD_LOCK_MINUTES = 15


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reason(reason: str) -> str:
    cleaned = (reason or "").strip()
    if not 3 <= len(cleaned) <= 500:
        raise ValueError("Cần ghi lý do (3–500 ký tự) khi xác thực lại.")
    return cleaned


class ConsoleAuthService:
    def __init__(self, store=None, google=None, vault=None, config=None, clock=None) -> None:
        self.store = store or console_store
        self._config = config or get_config().console
        self._google = google
        self._vault = vault
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # Dựng lười: thiếu cấu hình Google/TOTP chỉ lỗi ở đúng thao tác cần nó.
    def _google_client(self) -> GoogleOidcClient:
        if self._google is None:
            cfg = self._config
            self._google = GoogleOidcClient(
                cfg.google_client_id, cfg.google_client_secret, cfg.google_redirect_uri
            )
        return self._google

    def _totp(self) -> TotpVault:
        if self._vault is None:
            self._vault = TotpVault(self._config.totp_encryption_key, self._config.totp_issuer)
        return self._vault

    async def _open(self, member_id: str, method: str, google_sub: str | None = None) -> str:
        raw = secrets.token_urlsafe(32)
        await self.store.open_session(member_id, token_hash(raw), method, google_sub)
        return raw

    # ── Bước 1: xác định danh tính ───────────────────────────────────────────

    async def start_google(self) -> tuple[str, str]:
        """Trả (URL chuyển sang Google, secret gắn với trình duyệt cho cookie flow)."""
        state, browser, nonce = (secrets.token_urlsafe(32) for _ in range(3))
        verifier, challenge = new_pkce_pair()
        url = self._google_client().authorize_url(state, nonce, challenge)
        await self.store.create_auth_flow(token_hash(state), token_hash(browser), nonce, verifier)
        return url, browser

    async def finish_google(self, code: str, state: str, browser: str) -> str:
        logger.info(f"[finish_google] Step 1: validating inputs code_len={len(code)}, state_len={len(state)}, browser_len={len(browser)}")
        if not code or not state or not browser:
            logger.warning("[finish_google] Missing code, state, or browser cookie!")
            raise ConsoleAuthError("Thiếu dữ liệu đăng nhập Google.")
        logger.info(f"[finish_google] Step 2: consuming auth flow with state_hash={token_hash(state)[:10]}..., browser_hash={token_hash(browser)[:10]}...")
        flow = await self.store.consume_auth_flow(token_hash(state), token_hash(browser))
        if flow is None:
            logger.warning("[finish_google] consume_auth_flow returned None (no matching flow or expired > 10m)!")
            raise ConsoleAuthError("Phiên đăng nhập Google không hợp lệ hoặc đã quá 10 phút.")
        logger.info("[finish_google] Step 3: exchanging code with Google and verifying id_token...")
        identity = await asyncio.to_thread(
            self._google_client().login, code, flow["code_verifier"], flow["nonce"]
        )
        logger.info(f"[finish_google] Step 4: Google verified identity email={identity.email}, sub={identity.sub}")
        member = await self.store.get_login_member(identity.email)
        if member is None or member["status"] == "DISABLED":
            logger.warning(f"[finish_google] Member {identity.email} is None or DISABLED: {member}")
            raise ConsoleAuthError("Email này chưa được mời vào console.", "NOT_INVITED")
        logger.info(f"[finish_google] Step 5: opening session for member id={member['id']}")
        return await self._open(member["id"], "google", identity.sub)

    async def password_login(self, email: str, password: str) -> str:
        member = await self.store.get_login_member((email or "").strip())
        if (
            member is None or member["status"] == "DISABLED" or not member["password_hash"]
            or member.get("password_locked")
        ):
            raise ConsoleAuthError(_LOGIN_FAILED)
        if not verify_password(member["password_hash"], password or ""):
            await self.store.fail_password(member["id"], MAX_AUTH_FAILURES, PASSWORD_LOCK_MINUTES)
            raise ConsoleAuthError(_LOGIN_FAILED)
        return await self._open(member["id"], "password")

    # ── Bước 2: TOTP ─────────────────────────────────────────────────────────

    async def _load(self, raw: str, require_mfa: bool) -> dict:
        if not raw:
            raise ConsoleAuthError("Chưa đăng nhập console.")
        session = await self.store.get_session(token_hash(raw))
        if session is None:
            raise ConsoleAuthError("Chưa đăng nhập console.")
        cfg = self._config
        session_policy.check_session(
            session, self._clock(),
            ttl=timedelta(hours=cfg.session_ttl_hours),
            idle=timedelta(minutes=cfg.idle_timeout_minutes),
            require_mfa=require_mfa,
        )
        return session

    async def totp_enrollment_uri(self, raw: str) -> str:
        session = await self._load(raw, require_mfa=False)
        if session["totp_enabled"]:
            raise ConsoleAuthError("TOTP đã được bật cho tài khoản này.", "TOTP_ALREADY_ENROLLED")
        vault = self._totp()
        if session["totp_secret_enc"]:
            secret = vault.decrypt(session["totp_secret_enc"])
        else:
            secret = vault.new_secret()
            await self.store.set_totp_secret(session["member_id"], vault.encrypt(secret))
        return vault.provisioning_uri(secret, session["email"])

    async def _accept_code(self, session: dict, code: str, reason: str | None) -> None:
        if not session["totp_secret_enc"]:
            raise ConsoleAuthError("Tài khoản chưa đăng ký TOTP.", "TOTP_NOT_ENROLLED")
        vault = self._totp()
        step = vault.match_step(vault.decrypt(session["totp_secret_enc"]), code)
        if step is None:
            if await self.store.fail_totp(session["session_id"], session["member_id"], MAX_AUTH_FAILURES):
                raise ConsoleAuthError(
                    "Sai mã quá nhiều lần — phiên đã bị huỷ, hãy đăng nhập lại.", "TOO_MANY_ATTEMPTS"
                )
            raise ConsoleAuthError("Mã xác thực không đúng.", "TOTP_INVALID")
        await self.store.accept_totp(session["member_id"], session["session_id"], step, reason)

    async def verify_totp(self, raw: str, code: str) -> None:
        await self._accept_code(await self._load(raw, require_mfa=False), code, None)

    async def step_up(self, raw: str, code: str, reason: str) -> None:
        reason = _reason(reason)
        await self._accept_code(await self._load(raw, require_mfa=True), code, reason)

    # ── Dùng phiên ───────────────────────────────────────────────────────────

    async def resolve(self, raw: str, require_mfa: bool = True) -> ConsoleSession:
        session = await self._load(raw, require_mfa)
        await self.store.touch_session(session["session_id"])
        return ConsoleSession(
            session_id=session["session_id"],
            actor=ConsoleActor(session["member_id"], frozenset(session["roles"])),
            email=session["email"],
            display_name=session["display_name"],
            mfa_done=session["mfa_at"] is not None,
            totp_enabled=session["totp_enabled"],
            step_up_at=session["step_up_at"],
            totp_secret_set=session.get("totp_secret_enc") is not None,
        )

    async def authorize(self, raw: str, permission: str) -> ConsoleActor:
        session = await self.resolve(raw)
        access_policy.require(session.actor, permission)
        if permission in access_policy.STEP_UP_PERMISSIONS and not session_policy.step_up_fresh(
            session.step_up_at, self._clock(), timedelta(minutes=self._config.step_up_minutes)
        ):
            raise ConsoleAuthError("Thao tác này cần nhập lại mã TOTP kèm lý do.", "STEP_UP_REQUIRED")
        return session.actor

    async def authorize_any(self, raw: str, permissions: tuple[str, ...]) -> ConsoleActor:
        """Đọc dữ liệu dùng chung cho nhiều vai trò (vd. ảnh cắt cho cả người gán lẫn người duyệt)."""
        if any(p in access_policy.STEP_UP_PERMISSIONS for p in permissions):
            raise ValueError("authorize_any không dùng cho quyền cần step-up")
        session = await self.resolve(raw)
        if not any(access_policy.can(session.actor, p) for p in permissions):
            raise ConsoleAccessDenied("Bạn không có quyền thực hiện thao tác này.")
        return session.actor

    async def logout(self, raw: str) -> None:
        if not raw:
            return
        session = await self.store.get_session(token_hash(raw))
        if session is not None:
            await self.store.revoke_session(session["session_id"], session["member_id"])


console_auth_service = ConsoleAuthService()
