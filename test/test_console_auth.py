"""Đăng nhập AI Console (P1b): luật phiên, TOTP, mật khẩu, Google OIDC, ConsoleAuthService."""
import asyncio
import base64
import hashlib
import time
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pyotp
from cryptography.fernet import Fernet

from app.core.console.engines import session_policy
from app.core.console.services.auth_service import ConsoleAuthService
from app.core.exceptions import ConsoleAccessDenied, ConsoleAuthError
from app.infra.identity.google_oidc import GoogleIdentity, GoogleOidcClient, new_pkce_pair
from app.infra.identity.password import hash_password, verify_password
from app.infra.identity.totp import TotpVault

T0 = datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc)


def run(coro):
    return asyncio.run(coro)


def session(**overrides):
    base = {
        "revoked_at": None, "member_status": "ACTIVE", "created_at": T0,
        "last_seen_at": T0, "mfa_at": T0,
    }
    return {**base, **overrides}


class SessionPolicyTest(unittest.TestCase):
    TTL, IDLE = timedelta(hours=8), timedelta(minutes=30)

    def code_of(self, s, now=T0, require_mfa=True):
        try:
            session_policy.check_session(s, now, self.TTL, self.IDLE, require_mfa)
        except ConsoleAuthError as exc:
            return exc.code
        return "OK"

    def test_codes(self):
        self.assertEqual("OK", self.code_of(session()))
        self.assertEqual("SESSION_REVOKED", self.code_of(session(revoked_at=T0)))
        self.assertEqual("MEMBER_DISABLED", self.code_of(session(member_status="DISABLED")))
        self.assertEqual("SESSION_EXPIRED", self.code_of(
            session(last_seen_at=T0 + timedelta(hours=8)), now=T0 + timedelta(hours=8, minutes=1)))
        self.assertEqual("SESSION_IDLE", self.code_of(session(), now=T0 + timedelta(minutes=31)))
        self.assertEqual("MFA_REQUIRED", self.code_of(session(mfa_at=None)))
        self.assertEqual("OK", self.code_of(session(mfa_at=None), require_mfa=False))

    def test_step_up_window(self):
        window = timedelta(minutes=5)
        self.assertFalse(session_policy.step_up_fresh(None, T0, window))
        self.assertTrue(session_policy.step_up_fresh(T0, T0 + window, window))
        self.assertFalse(session_policy.step_up_fresh(T0, T0 + window + timedelta(seconds=1), window))


class TotpVaultTest(unittest.TestCase):
    def setUp(self):
        self.vault = TotpVault(Fernet.generate_key().decode(), "Test")
        self.secret = self.vault.new_secret()

    def test_secret_round_trip_and_uri(self):
        encrypted = self.vault.encrypt(self.secret)
        self.assertNotIn(self.secret, encrypted)
        self.assertEqual(self.secret, self.vault.decrypt(encrypted))
        self.assertTrue(self.vault.provisioning_uri(self.secret, "a@x.vn").startswith("otpauth://totp/"))

    def test_missing_or_bad_key_is_config_error(self):
        for key in ("", "not-a-fernet-key"):
            with self.assertRaises(ConsoleAuthError) as ctx:
                TotpVault(key, "Test")
            self.assertEqual("NOT_CONFIGURED", ctx.exception.code)

    def test_match_step_accepts_one_step_drift_only(self):
        now = time.time()
        totp = pyotp.TOTP(self.secret)
        current = int(now // 30)
        self.assertEqual(current, TotpVault.match_step(self.secret, totp.at(now), now))
        self.assertEqual(current + 1, TotpVault.match_step(self.secret, totp.at(now + 30), now))
        self.assertIsNone(TotpVault.match_step(self.secret, totp.at(now + 90), now))
        self.assertIsNone(TotpVault.match_step(self.secret, "12a456", now))
        self.assertIsNone(TotpVault.match_step(self.secret, "", now))
        self.assertIsNone(TotpVault.match_step(self.secret, "١٢٣٤٥٦", now))  # chữ số không phải ASCII


class PasswordTest(unittest.TestCase):
    def test_hash_and_verify(self):
        hashed = hash_password("đủ-dài-12-ký-tự")
        self.assertTrue(verify_password(hashed, "đủ-dài-12-ký-tự"))
        self.assertFalse(verify_password(hashed, "sai"))
        self.assertFalse(verify_password("không-phải-hash", "x"))


class GoogleOidcTest(unittest.TestCase):
    def setUp(self):
        self.client = GoogleOidcClient("cid", "csecret", "http://localhost:8090/cb")

    def test_pkce_challenge_is_s256_of_verifier(self):
        verifier, challenge = new_pkce_pair()
        expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
        self.assertEqual(expected.decode(), challenge)

    def test_authorize_url(self):
        query = parse_qs(urlparse(self.client.authorize_url("st", "no", "ch")).query)
        self.assertEqual(["S256"], query["code_challenge_method"])
        self.assertEqual(["st"], query["state"])
        self.assertEqual(["no"], query["nonce"])
        self.assertEqual(["openid email"], query["scope"])
        self.assertNotIn("client_secret", query)

    def test_not_configured(self):
        with self.assertRaises(ConsoleAuthError) as ctx:
            GoogleOidcClient("", "", "").authorize_url("s", "n", "c")
        self.assertEqual("NOT_CONFIGURED", ctx.exception.code)

    def test_verify_checks_nonce_and_verified_email(self):
        target = "app.infra.identity.google_oidc.google_id_token.verify_oauth2_token"
        good = {"sub": "1", "email": "a@x.vn", "email_verified": True, "nonce": "n"}
        with patch(target, return_value=good):
            self.assertEqual(GoogleIdentity("1", "a@x.vn"), self.client._verify("t", "n"))
            with self.assertRaises(ConsoleAuthError):
                self.client._verify("t", "khác")
        with patch(target, return_value={**good, "email_verified": False}):
            with self.assertRaises(ConsoleAuthError):
                self.client._verify("t", "n")
        with patch(target, side_effect=ValueError("bad signature")):
            with self.assertRaises(ConsoleAuthError):
                self.client._verify("t", "n")


# ── ConsoleAuthService trên store giả ─────────────────────────────────────────

class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now


class FakeStore:
    def __init__(self, clock):
        self.clock, self.flows, self.members, self.sessions, self.audit = clock, {}, {}, {}, []

    def add_member(self, email, roles=(), status="INVITED", password_hash=None):
        member_id = f"m{len(self.members) + 1}"
        self.members[member_id] = {
            "id": member_id, "email": email, "status": status, "google_sub": None,
            "password_hash": password_hash, "totp_secret_enc": None, "totp_enabled": False,
            "last_step": -1, "roles": list(roles),
        }
        return member_id

    async def create_auth_flow(self, state_hash, browser_hash, nonce, verifier):
        self.flows[state_hash] = (browser_hash, nonce, verifier)

    async def consume_auth_flow(self, state_hash, browser_hash):
        flow = self.flows.pop(state_hash, None)
        if not flow or flow[0] != browser_hash:
            return None
        return {"nonce": flow[1], "code_verifier": flow[2]}

    async def get_login_member(self, email):
        for m in self.members.values():
            if m["email"].lower() == email.lower():
                return {k: m[k] for k in (
                    "id", "status", "google_sub", "password_hash", "totp_secret_enc", "totp_enabled")}
        return None

    async def open_session(self, member_id, token_hash, method, google_sub=None):
        member = self.members[member_id]
        if google_sub is not None:
            if member["google_sub"] not in (None, google_sub):
                raise ConsoleAuthError("mismatch")
            member["google_sub"] = google_sub
        now = self.clock()
        self.sessions[token_hash] = {
            "session_id": f"s{len(self.sessions) + 1}", "member_id": member_id, "created_at": now,
            "last_seen_at": now, "mfa_at": None, "step_up_at": None, "revoked_at": None,
        }
        self.audit.append(f"auth.login:{method}")

    def _by_id(self, session_id):
        return next(s for s in self.sessions.values() if s["session_id"] == session_id)

    async def get_session(self, token_hash):
        s = self.sessions.get(token_hash)
        if s is None:
            return None
        m = self.members[s["member_id"]]
        return {**s, "email": m["email"], "display_name": m["email"], "member_status": m["status"],
                "totp_secret_enc": m["totp_secret_enc"], "totp_enabled": m["totp_enabled"],
                "roles": sorted(m["roles"])}

    async def touch_session(self, session_id):
        self._by_id(session_id)["last_seen_at"] = self.clock()

    async def set_totp_secret(self, member_id, secret_enc):
        self.members[member_id]["totp_secret_enc"] = secret_enc

    async def accept_totp(self, member_id, session_id, step, step_up_reason=None):
        member = self.members[member_id]
        if member["status"] == "DISABLED" or step <= member["last_step"]:
            raise ConsoleAuthError("used", "TOTP_INVALID")
        member.update(last_step=step, totp_enabled=True,
                      status="ACTIVE" if member["status"] == "INVITED" else member["status"])
        key = "mfa_at" if step_up_reason is None else "step_up_at"
        self._by_id(session_id)[key] = self.clock()
        self.audit.append("auth.mfa" if step_up_reason is None else f"auth.step_up:{step_up_reason}")

    async def revoke_session(self, session_id, member_id):
        self._by_id(session_id)["revoked_at"] = self.clock()


class FakeGoogle:
    def __init__(self, identity):
        self.identity, self.state = identity, None

    def authorize_url(self, state, nonce, challenge):
        self.state = state
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}"

    def login(self, code, verifier, nonce):
        return self.identity


class ConsoleAuthServiceTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.store = FakeStore(self.clock)
        self.vault = TotpVault(Fernet.generate_key().decode(), "Test")
        self.google = FakeGoogle(GoogleIdentity("g-1", "lead@x.vn"))
        config = SimpleNamespace(session_ttl_hours=8, idle_timeout_minutes=30, step_up_minutes=5)
        self.service = ConsoleAuthService(self.store, self.google, self.vault, config, self.clock)

    def code(self, err):
        return err.exception.code

    def login_google(self):
        _, browser = run(self.service.start_google())
        return run(self.service.finish_google("code", self.google.state, browser))

    def enroll_and_verify(self, raw):
        uri = run(self.service.totp_enrollment_uri(raw))
        secret = parse_qs(urlparse(uri).query)["secret"][0]
        run(self.service.verify_totp(raw, pyotp.TOTP(secret).now()))
        return secret

    def test_google_login_needs_invite_then_totp(self):
        with self.assertRaises(ConsoleAuthError) as err:
            self.login_google()
        self.assertEqual("NOT_INVITED", self.code(err))

        self.store.add_member("lead@x.vn", roles=["ai_lead"])
        raw = self.login_google()
        with self.assertRaises(ConsoleAuthError) as err:
            run(self.service.resolve(raw))
        self.assertEqual("MFA_REQUIRED", self.code(err))

        self.enroll_and_verify(raw)
        session = run(self.service.resolve(raw))
        self.assertTrue(session.mfa_done)
        self.assertEqual(frozenset({"ai_lead"}), session.actor.roles)
        self.assertEqual("ACTIVE", self.store.members["m1"]["status"])

    def test_disabled_member_cannot_log_in(self):
        self.store.add_member("lead@x.vn", status="DISABLED")
        with self.assertRaises(ConsoleAuthError) as err:
            self.login_google()
        self.assertEqual("NOT_INVITED", self.code(err))

    def test_auth_flow_is_one_time_and_bound_to_browser(self):
        self.store.add_member("lead@x.vn")
        _, browser = run(self.service.start_google())
        with self.assertRaises(ConsoleAuthError):
            run(self.service.finish_google("code", self.google.state, "trình-duyệt-khác"))
        _, browser = run(self.service.start_google())
        run(self.service.finish_google("code", self.google.state, browser))
        with self.assertRaises(ConsoleAuthError):
            run(self.service.finish_google("code", self.google.state, browser))

    def test_totp_code_cannot_be_replayed(self):
        self.store.add_member("lead@x.vn")
        raw = self.login_google()
        secret = self.enroll_and_verify(raw)
        with self.assertRaises(ConsoleAuthError) as err:
            run(self.service.verify_totp(raw, pyotp.TOTP(secret).now()))
        self.assertEqual("TOTP_INVALID", self.code(err))

    def test_sensitive_permission_needs_fresh_step_up_with_reason(self):
        self.store.add_member("lead@x.vn", roles=["ai_lead"])
        raw = self.login_google()
        secret = self.enroll_and_verify(raw)
        run(self.service.authorize(raw, "ai:metrics:read"))
        with self.assertRaises(ConsoleAuthError) as err:
            run(self.service.authorize(raw, "ai:model:promote"))
        self.assertEqual("STEP_UP_REQUIRED", self.code(err))

        next_code = pyotp.TOTP(secret).at(time.time() + 30)
        with self.assertRaises(ValueError):
            run(self.service.step_up(raw, next_code, "  "))
        run(self.service.step_up(raw, next_code, "promote v3 sau khi đo golden"))
        self.assertIn("auth.step_up:promote v3 sau khi đo golden", self.store.audit)
        run(self.service.authorize(raw, "ai:model:promote"))

        self.clock.now += timedelta(minutes=6)
        with self.assertRaises(ConsoleAuthError) as err:
            run(self.service.authorize(raw, "ai:model:promote"))
        self.assertEqual("STEP_UP_REQUIRED", self.code(err))

    def test_role_still_decides_after_login(self):
        self.store.add_member("lead@x.vn", roles=["ai_annotator"])
        raw = self.login_google()
        self.enroll_and_verify(raw)
        with self.assertRaises(ConsoleAccessDenied):
            run(self.service.authorize(raw, "ai:model:promote"))

    def test_idle_and_absolute_expiry(self):
        self.store.add_member("lead@x.vn")
        raw = self.login_google()
        self.enroll_and_verify(raw)
        self.clock.now += timedelta(minutes=31)
        with self.assertRaises(ConsoleAuthError) as err:
            run(self.service.resolve(raw))
        self.assertEqual("SESSION_IDLE", self.code(err))

        raw = self.login_google()
        self.store.members["m1"]["last_step"] = -1  # TOTP mới cho phiên thứ hai trong test
        self.enroll_and_verify_existing(raw)
        for _ in range(25):  # chạm phiên mỗi 20 phút → không rảnh, nhưng vượt 8 giờ
            self.clock.now += timedelta(minutes=20)
            try:
                run(self.service.resolve(raw))
            except ConsoleAuthError as exc:
                self.assertEqual("SESSION_EXPIRED", exc.code)
                break
        else:
            self.fail("Phiên không hết hạn sau 8 giờ")

    def enroll_and_verify_existing(self, raw):
        secret = self.vault.decrypt(self.store.members["m1"]["totp_secret_enc"])
        run(self.service.verify_totp(raw, pyotp.TOTP(secret).now()))

    def test_password_login_errors_are_generic(self):
        self.store.add_member("google-only@x.vn")
        self.store.add_member("admin@x.vn", roles=["ai_console_admin"],
                              password_hash=hash_password("mật-khẩu-đủ-dài"))
        messages = set()
        for email, password in (("admin@x.vn", "sai"), ("google-only@x.vn", "x"), ("không@có.vn", "x")):
            with self.assertRaises(ConsoleAuthError) as err:
                run(self.service.password_login(email, password))
            messages.add(str(err.exception))
        self.assertEqual(1, len(messages))
        raw = run(self.service.password_login("admin@x.vn", "mật-khẩu-đủ-dài"))
        with self.assertRaises(ConsoleAuthError) as err:
            run(self.service.resolve(raw))
        self.assertEqual("MFA_REQUIRED", self.code(err))

    def test_logout_revokes(self):
        self.store.add_member("lead@x.vn")
        raw = self.login_google()
        self.enroll_and_verify(raw)
        run(self.service.logout(raw))
        with self.assertRaises(ConsoleAuthError) as err:
            run(self.service.resolve(raw))
        self.assertEqual("SESSION_REVOKED", self.code(err))


if __name__ == "__main__":
    unittest.main()
