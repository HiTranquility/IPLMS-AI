"""A-25 (AUDIT-006): các route Settings/Sessions qua HTTP thật — quyền, step-up, DTO. Service được giả lập."""
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.rest.console_access import SESSION_COOKIE
from app.core.console import console_tools_service
from app.core.console.dtos import ConsoleActor, ConsoleSession
from app.core.console.services import console_auth_service

H = {"X-Console-Request": "1", "Cookie": f"{SESSION_COOKIE}=tok"}
BASE = "/console/api/tools"


def _session(roles: tuple[str, ...], fresh_step_up: bool = False) -> ConsoleSession:
    return ConsoleSession(
        session_id="sess-1",
        actor=ConsoleActor(member_id="m-1", roles=frozenset(roles), session_id="sess-1"),
        email="m-1@iplms.internal",
        display_name="Member 1",
        mfa_done=True,
        totp_enabled=True,
        step_up_at=datetime.now(timezone.utc) if fresh_step_up else None,
        totp_secret_set=True,
    )


class ConsoleSettingsHttpTest(unittest.TestCase):
    def setUp(self):
        from app.console_main import app

        self.client = TestClient(app)
        self.patches = [
            patch.object(console_tools_service, "update_policy_settings", new_callable=AsyncMock, return_value={}),
            patch.object(console_tools_service, "update_compute_settings", new_callable=AsyncMock, return_value={}),
            patch.object(console_tools_service, "get_runtime_settings", new_callable=AsyncMock, return_value={}),
            patch.object(console_tools_service, "revoke_session_by_id", new_callable=AsyncMock, return_value={"revoked": True}),
        ]
        self.mocks = [p.start() for p in self.patches]

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _as(self, roles, fresh_step_up=False):
        return patch.object(console_auth_service, "resolve", new_callable=AsyncMock,
                            return_value=_session(roles, fresh_step_up))

    def test_policy_can_step_up_khi_chua_nhap_lai_totp(self):
        with self._as(("ai_lead",)):
            r = self.client.put(f"{BASE}/settings/policy", json={"rag_top_k": 6, "reason": "đo held-out"}, headers=H)
        self.assertEqual("STEP_UP_REQUIRED", r.json()["code"])
        self.mocks[0].assert_not_awaited()

    def test_policy_bat_buoc_ly_do(self):
        with self._as(("ai_lead",), fresh_step_up=True):
            r = self.client.put(f"{BASE}/settings/policy", json={"rag_top_k": 6}, headers=H)
        self.assertEqual(422, r.status_code)

    def test_policy_lead_da_step_up_luu_duoc(self):
        with self._as(("ai_lead",), fresh_step_up=True):
            r = self.client.put(f"{BASE}/settings/policy", json={"rag_top_k": 6, "reason": "đo held-out"}, headers=H)
        self.assertEqual(200, r.status_code)
        self.assertEqual("đo held-out", self.mocks[0].await_args.args[1]["reason"])

    def test_policy_ml_engineer_bi_tu_choi(self):
        with self._as(("ai_ml_engineer",), fresh_step_up=True):
            r = self.client.put(f"{BASE}/settings/policy", json={"rag_top_k": 6, "reason": "thử"}, headers=H)
        self.assertEqual(403, r.status_code)

    def test_compute_khong_nhan_provider_openai_hay_base_url(self):
        with self._as(("ai_ml_engineer",)):
            r = self.client.put(f"{BASE}/settings/compute", json={"llm_provider": "openai"}, headers=H)
            self.assertEqual(422, r.status_code)
            r = self.client.put(
                f"{BASE}/settings/compute",
                json={"llm_provider": "ollama", "llm_base_url": "http://evil.example/v1"},
                headers=H,
            )
        self.assertEqual(200, r.status_code)
        self.assertNotIn("llm_base_url", self.mocks[1].await_args.args[1])

    def test_annotator_khong_xem_settings(self):
        with self._as(("ai_annotator",)):
            r = self.client.get(f"{BASE}/settings", headers=H)
        self.assertEqual(403, r.status_code)

    def test_revoke_session_id_khong_phai_uuid_tra_422(self):
        with self._as(("ai_console_admin",)):
            r = self.client.post(f"{BASE}/sessions/khong-phai-uuid/revoke", json={"reason": "dọn"}, headers=H)
            self.assertEqual(422, r.status_code)
            r = self.client.post(
                f"{BASE}/sessions/3f1c2a64-5b7d-4e8f-9a01-23456789abcd/revoke", json={"reason": "dọn"}, headers=H
            )
        self.assertEqual(200, r.status_code)


if __name__ == "__main__":
    unittest.main()
