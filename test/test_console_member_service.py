"""Service thành viên AI Console (fake store) + kiểm DB thật khi có AI_TEST_DATABASE_URL."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.console.dtos import ConsoleActor
from app.core.console.services.member_service import ConsoleMemberService
from app.core.exceptions import ConsoleAccessDenied, ConsoleStoreError
from app.infra.database.console_store import ConsoleStore

ADMIN = ConsoleActor(member_id="admin-1", roles=frozenset({"ai_console_admin"}))
LEAD = ConsoleActor(member_id="lead-1", roles=frozenset({"ai_lead"}))


def run(coro):
    return asyncio.run(coro)


class ConsoleMemberServiceTest(unittest.TestCase):
    def setUp(self):
        self.store = AsyncMock()
        self.service = ConsoleMemberService(store=self.store)

    def test_only_console_admin_invites(self):
        with self.assertRaises(ConsoleAccessDenied):
            run(self.service.invite(LEAD, "a@example.com", "A", "onboard"))
        self.store.invite_member.assert_not_awaited()

    def test_invite_validates_email_and_requires_reason(self):
        with self.assertRaises(ValueError):
            run(self.service.invite(ADMIN, "not-an-email", "A", "onboard"))
        with self.assertRaises(ValueError):
            run(self.service.invite(ADMIN, "a@example.com", "A", "  "))
        run(self.service.invite(ADMIN, " a@example.com ", " A ", "onboard"))
        self.store.invite_member.assert_awaited_once_with("a@example.com", "A", "admin-1", "onboard")

    def test_admin_cannot_grant_role_to_self(self):
        with self.assertRaises(ConsoleAccessDenied):
            run(self.service.grant_role(ADMIN, "admin-1", "ai_lead", "self grant"))
        self.store.grant_role.assert_not_awaited()

    def test_grant_rejects_unknown_role(self):
        with self.assertRaises(ValueError):
            run(self.service.grant_role(ADMIN, "m-2", "Moderator", "wrong role"))

    def test_audit_needs_audit_permission(self):
        with self.assertRaises(ConsoleAccessDenied):
            run(self.service.list_audit(ConsoleActor("x", frozenset({"ai_analyst"}))))
        with self.assertRaises(ValueError):
            run(self.service.list_audit(LEAD, limit=0))
        run(self.service.list_audit(LEAD, limit=20))
        self.store.list_audit.assert_awaited_once_with(20)


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class ConsoleStoreDatabaseTest(unittest.TestCase):
    def setUp(self):
        import psycopg2
        from psycopg2 import sql

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        self.schema = "console_test_" + uuid4().hex
        self.admin = psycopg2.connect(base_url)
        with self.admin, self.admin.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        sep = "&" if "?" in base_url else "?"
        self.url = f"{base_url}{sep}options=-csearch_path%3D{self.schema}"
        self.store = ConsoleStore(self.url)

    def tearDown(self):
        from psycopg2 import sql

        with self.admin, self.admin.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def test_changes_are_audited_and_audit_is_append_only(self):
        import psycopg2

        actor_id = str(uuid4())
        member = run(self.store.invite_member("Lab@Example.com", "Lab", actor_id, "onboard"))
        with self.assertRaises(ConsoleStoreError):
            run(self.store.invite_member("lab@example.com", "Dup", actor_id, "dup"))

        self.assertTrue(run(self.store.grant_role(member["id"], "ai_lead", actor_id, "lead")))
        self.assertFalse(run(self.store.grant_role(member["id"], "ai_lead", actor_id, "again")))
        self.assertEqual(["ai_lead"], run(self.store.get_member(member["id"]))["roles"])
        self.assertTrue(run(self.store.revoke_role(member["id"], "ai_lead", actor_id, "done")))

        actions = [e["action"] for e in run(self.store.list_audit(10))]
        self.assertCountEqual(["member.invite", "role.grant:ai_lead", "role.revoke:ai_lead"], actions)

        with psycopg2.connect(self.url) as conn, conn.cursor() as cur:
            with self.assertRaises(psycopg2.Error):
                cur.execute("UPDATE audit_event SET reason = 'sửa'")
        with psycopg2.connect(self.url) as conn, conn.cursor() as cur:
            with self.assertRaises(psycopg2.Error):
                cur.execute("DELETE FROM audit_event")


if __name__ == "__main__":
    unittest.main()
