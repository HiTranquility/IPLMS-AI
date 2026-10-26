"""Luồng HTTP AI Console trên Postgres thật: mật khẩu khẩn cấp → TOTP → mời → cấp quyền → audit."""
import asyncio
import hashlib
import os
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import pyotp
from cryptography.fernet import Fernet

from app.infra.database.console_store import ConsoleStore
from app.infra.identity.password import hash_password
from app.infra.identity.totp import TotpVault

H = {"X-Console-Request": "1"}
PASSWORD = "mật-khẩu-khẩn-cấp-đủ-dài"


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class ConsoleHttpFlowTest(unittest.TestCase):
    def setUp(self):
        import psycopg2
        from psycopg2 import sql
        from fastapi.testclient import TestClient

        from app.console_main import app
        from app.core.console.services import console_auth_service, console_member_service

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        self.schema = "console_http_" + uuid4().hex
        self.admin_conn = psycopg2.connect(base_url)
        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        sep = "&" if "?" in base_url else "?"
        self.url = f"{base_url}{sep}options=-csearch_path%3D{self.schema}"

        store = ConsoleStore(self.url)
        vault = TotpVault(Fernet.generate_key().decode(), "Test")
        self.secret = vault.new_secret()
        self.admin_id = asyncio.run(store.create_emergency_admin(
            "admin@x.vn", "Admin", hash_password(PASSWORD), vault.encrypt(self.secret), "ai_console_admin"
        ))
        self.patches = [
            patch.object(console_auth_service, "store", store),
            patch.object(console_auth_service, "_vault", vault),
            patch.object(console_member_service, "store", store),
        ]
        for p in self.patches:
            p.start()
        self.client = TestClient(app)

    def tearDown(self):
        from psycopg2 import sql

        for p in self.patches:
            p.stop()
        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin_conn.close()

    def body(self, response):
        return response.json()

    def test_full_flow(self):
        import psycopg2

        c = self.client
        login = {"email": "admin@x.vn", "password": PASSWORD}
        r = c.post("/api/auth/password", json=login)
        self.assertEqual((403, "FORBIDDEN"), (r.status_code, self.body(r)["code"]))  # thiếu header CSRF
        r = c.post("/api/auth/password", json={**login, "password": "sai"}, headers=H)
        self.assertEqual(401, r.status_code)

        r = c.post("/api/auth/password", json=login, headers=H)
        self.assertEqual(200, r.status_code)
        raw = c.cookies.get("ai_console_session")
        self.assertTrue(raw)
        set_cookie = r.headers["set-cookie"].lower()
        self.assertIn("httponly", set_cookie)
        self.assertIn("samesite=strict", set_cookie)

        me = self.body(c.get("/api/me"))["data"][0]
        self.assertEqual((False, []), (me["mfa_done"], me["permissions"]))
        self.assertEqual((False, True), (me["totp_enabled"], me["totp_pending"]))  # khoá từ CLI, chưa xác nhận
        invite = {"email": "lab@x.vn", "display_name": "Lab", "reason": "onboard lab"}
        r = c.post("/api/members", json=invite, headers=H)
        self.assertEqual((401, "MFA_REQUIRED"), (r.status_code, self.body(r)["code"]))

        code = pyotp.TOTP(self.secret).now()
        self.assertEqual(200, c.post("/api/auth/totp", json={"code": code}, headers=H).status_code)
        r = c.post("/api/auth/totp", json={"code": code}, headers=H)
        self.assertEqual((401, "TOTP_INVALID"), (r.status_code, self.body(r)["code"]))

        me = self.body(c.get("/api/me"))["data"][0]
        self.assertEqual(["ai:member:manage", "ai:audit:read"], me["permissions"])
        self.assertEqual((True, False), (me["totp_enabled"], me["totp_pending"]))

        r = c.post("/api/members", json=invite, headers=H)
        self.assertEqual(200, r.status_code)
        new_id = self.body(r)["data"][0]["id"]
        reason = {"reason": "trưởng nhóm AI"}
        r = c.post(f"/api/members/{self.admin_id}/roles/ai_lead", json=reason, headers=H)
        self.assertEqual(403, r.status_code)  # không tự cấp quyền cho mình
        r = c.post(f"/api/members/{new_id}/roles/ai_lead", json=reason, headers=H)
        self.assertEqual(True, self.body(r)["data"][0]["changed"])
        members = {m["email"]: m["roles"] for m in self.body(c.get("/api/members"))["data"]}
        self.assertEqual({"admin@x.vn": ["ai_console_admin"], "lab@x.vn": ["ai_lead"]}, members)
        # Admin quản người, không đọc chat log (PROB-049 §3).
        self.assertEqual(403, c.get("/api/copilot/turns").status_code)

        actions = {e["action"] for e in self.body(c.get("/api/audit"))["data"]}
        self.assertTrue({
            "system.bootstrap_admin", "auth.login:password", "auth.mfa",
            "member.invite", "role.grant:ai_lead",
        } <= actions)

        with psycopg2.connect(self.url) as conn, conn.cursor() as cur:
            cur.execute("SELECT token_hash FROM console_session")
            stored = [row[0] for row in cur.fetchall()]
        self.assertNotIn(raw, stored)  # DB không giữ token gốc
        self.assertIn(hashlib.sha256(raw.encode()).hexdigest(), stored)

        self.assertEqual(200, c.post("/api/auth/logout", headers=H).status_code)
        c.cookies.set("ai_console_session", raw, path="/")
        r = c.get("/api/me")
        self.assertEqual((401, "SESSION_REVOKED"), (r.status_code, self.body(r)["code"]))

    def test_security_headers_and_no_docs(self):
        r = self.client.get("/api/health")
        self.assertEqual(200, r.status_code)
        self.assertEqual("DENY", r.headers["x-frame-options"])
        self.assertEqual("no-store", r.headers["cache-control"])
        self.assertEqual(404, self.client.get("/console/api/health").status_code)
        self.assertEqual(404, self.client.get("/console").status_code)
        self.assertEqual(404, self.client.get("/console/api/me").status_code)
        self.assertEqual(404, self.client.get("/docs").status_code)
        self.assertEqual(404, self.client.get("/openapi.json").status_code)
        self.assertEqual(404, self.client.get("/redoc").status_code)


if __name__ == "__main__":
    unittest.main()
