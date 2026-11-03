"""Ma trận vai trò × quyền của AI Console và chốt chặn API (PROB-049 §3 / ADR-0048)."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.rest.console_access import (
    CSRF_HEADER,
    FLOW_COOKIE,
    SESSION_COOKIE,
    clear_flow_cookie,
    clear_session_cookie,
    require_any_permission,
    require_permission,
    require_same_origin_write,
    set_flow_cookie,
    set_session_cookie,
)
from app.core.console.dtos import ConsoleActor, ConsoleSession
from app.core.console.engines import access_policy as policy
from app.core.console import auth_service
from app.core.exceptions import ConsoleAccessDenied, ConsoleAuthError

# Bảng kỳ vọng chép tay từ tài liệu — cố ý lặp lại để đổi quyền phải sửa ở hai nơi.
EXPECTED = {
    "ai:metrics:read": {"ai_analyst", "ai_reviewer", "ai_data_engineer", "ai_ml_engineer", "ai_lead"},
    "ai:task:label": {"ai_annotator", "ai_reviewer"},
    "ai:label:approve": {"ai_reviewer", "ai_lead"},
    "ai:chatlog:read": {"ai_analyst", "ai_reviewer", "ai_ml_engineer", "ai_lead"},
    "ai:pii:reveal": {"ai_data_engineer", "ai_lead"},
    "ai:pipeline:manage": {"ai_data_engineer", "ai_lead"},
    "ai:dataset:snapshot": {"ai_data_engineer", "ai_ml_engineer", "ai_lead"},
    "ai:golden:freeze": {"ai_lead"},
    "ai:model:evaluate": {"ai_ml_engineer", "ai_lead"},
    "ai:model:propose": {"ai_ml_engineer", "ai_lead"},
    "ai:model:promote": {"ai_lead"},
    "ai:prompt:edit": {"ai_ml_engineer", "ai_lead"},
    "ai:policy:threshold": {"ai_lead"},
    "ai:member:manage": {"ai_console_admin"},
    "ai:audit:read": {"ai_lead", "ai_console_admin"},
}


def actor(*roles, member_id="m-1"):
    return ConsoleActor(member_id=member_id, roles=frozenset(roles))


class ConsoleAccessPolicyTest(unittest.TestCase):
    def test_matrix_matches_documented_table_cell_by_cell(self):
        self.assertEqual(set(EXPECTED), set(policy.PERMISSIONS))
        self.assertEqual(7, len(policy.ROLES))
        for permission, allowed in EXPECTED.items():
            for role in policy.ROLES:
                with self.subTest(permission=permission, role=role):
                    self.assertEqual(role in allowed, policy.can(actor(role), permission))

    def test_all_105_role_permission_pairs_exhaustive(self):
        """Kiểm tra toàn bộ 7 vai trò x 15 quyền = 105 tổ hợp allow/deny chính xác."""
        total_evaluations = 0
        for permission in policy.PERMISSIONS:
            allowed_roles = EXPECTED[permission]
            for role in policy.ROLES:
                total_evaluations += 1
                should_allow = role in allowed_roles
                actual_allowed = policy.can(actor(role), permission)
                self.assertEqual(
                    should_allow,
                    actual_allowed,
                    f"Sai quyền: role='{role}', perm='{permission}' phải là {should_allow}",
                )
        self.assertEqual(105, total_evaluations)

    def test_multiple_roles_union_permissions(self):
        """Thành viên mang nhiều vai trò phải được gộp toàn bộ quyền tương ứng."""
        multi_actor = actor("ai_annotator", "ai_reviewer")
        # Annotator có task:label, Reviewer có label:approve và chatlog:read
        self.assertTrue(policy.can(multi_actor, "ai:task:label"))
        self.assertTrue(policy.can(multi_actor, "ai:label:approve"))
        self.assertTrue(policy.can(multi_actor, "ai:chatlog:read"))
        # Nhưng cả hai đều không có quyền model:promote hay member:manage
        self.assertFalse(policy.can(multi_actor, "ai:model:promote"))
        self.assertFalse(policy.can(multi_actor, "ai:member:manage"))

    def test_empty_roles_cannot_do_anything(self):
        """Actor không có vai trò nào (empty roles) bị từ chối trên toàn bộ 15 quyền."""
        empty_actor = actor()
        for perm in policy.PERMISSIONS:
            with self.subTest(permission=perm):
                self.assertFalse(policy.can(empty_actor, perm))
                with self.assertRaises(ConsoleAccessDenied):
                    policy.require(empty_actor, perm)

    def test_least_privilege_and_separation_of_duties(self):
        """Kiểm chứng nguyên tắc đặc quyền tối thiểu và tách biệt nhiệm vụ trọng yếu."""
        # Annotator không được tự duyệt nhãn (nguyên tắc bốn mắt)
        self.assertFalse(policy.can(actor("ai_annotator"), "ai:label:approve"))
        # Reviewer không được sửa prompt hệ thống hay đóng băng golden dataset
        self.assertFalse(policy.can(actor("ai_reviewer"), "ai:prompt:edit"))
        self.assertFalse(policy.can(actor("ai_reviewer"), "ai:golden:freeze"))
        # ML Engineer không thể tự promote model lên production nếu không có quyền lead
        self.assertFalse(policy.can(actor("ai_ml_engineer"), "ai:model:promote"))
        # ML Engineer không được tự tiện xem PII người dùng
        self.assertFalse(policy.can(actor("ai_ml_engineer"), "ai:pii:reveal"))
        # Data Engineer không được sửa prompt AI Copilot
        self.assertFalse(policy.can(actor("ai_data_engineer"), "ai:prompt:edit"))
        # Analyst là vai trò read-only phân tích, không có quyền can thiệp nhãn/prompt/model
        analyst = actor("ai_analyst")
        write_perms = {"ai:task:label", "ai:label:approve", "ai:prompt:edit", "ai:model:promote", "ai:golden:freeze"}
        for p in write_perms:
            self.assertFalse(policy.can(analyst, p))

    def test_console_admin_manages_people_not_data(self):
        data_permissions = set(EXPECTED) - {"ai:member:manage", "ai:audit:read"}
        for permission in data_permissions:
            self.assertFalse(policy.can(actor("ai_console_admin"), permission))

    def test_platform_roles_get_nothing(self):
        for permission in policy.PERMISSIONS:
            self.assertFalse(policy.can(actor("Admin", "Moderator"), permission))

    def test_unknown_permission_fails_loudly(self):
        with self.assertRaises(ValueError):
            policy.can(actor("ai_lead"), "ai:model:promot")

    def test_require_raises_access_denied(self):
        with self.assertRaises(ConsoleAccessDenied):
            policy.require(actor("ai_annotator"), "ai:label:approve")
        policy.require(actor("ai_reviewer"), "ai:label:approve")

    def test_four_eyes_rejects_same_person(self):
        with self.assertRaises(ConsoleAccessDenied):
            policy.require_second_person(actor("ai_lead", member_id="m-1"), "m-1")
        policy.require_second_person(actor("ai_lead", member_id="m-2"), "m-1")

    def test_step_up_covers_sensitive_actions_only_from_catalog(self):
        self.assertTrue(policy.STEP_UP_PERMISSIONS <= set(policy.PERMISSIONS))
        self.assertEqual(
            {"ai:pii:reveal", "ai:golden:freeze", "ai:model:promote", "ai:policy:threshold"},
            set(policy.STEP_UP_PERMISSIONS),
        )

    def test_validate_role(self):
        self.assertEqual("ai_lead", policy.validate_role("ai_lead"))
        with self.assertRaises(ValueError):
            policy.validate_role("moderator")
        with self.assertRaises(ValueError):
            policy.validate_role("root")
        with self.assertRaises(ValueError):
            policy.validate_role("")


# ── Bộ test hồi quy API Dependency & Chốt chặn CSRF ──────────────────────────


def _build_test_app() -> FastAPI:
    app = FastAPI(title="Console Access Test App")

    @app.exception_handler(ConsoleAuthError)
    async def _auth_error(_: Request, exc: ConsoleAuthError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"success": False, "total": 0, "message": str(exc), "data": [], "code": exc.code},
        )

    @app.exception_handler(ConsoleAccessDenied)
    async def _access_denied(_: Request, exc: ConsoleAccessDenied) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"success": False, "total": 0, "message": str(exc), "data": [], "code": "FORBIDDEN"},
        )

    @app.get("/test/metrics")
    async def read_metrics(actor: ConsoleActor = Depends(require_permission("ai:metrics:read"))):
        return {"success": True, "member_id": actor.member_id, "roles": sorted(list(actor.roles))}

    @app.post("/test/golden/freeze", dependencies=[Depends(require_same_origin_write)])
    async def freeze_golden(actor: ConsoleActor = Depends(require_permission("ai:golden:freeze"))):
        return {"success": True, "member_id": actor.member_id}

    @app.get("/test/label-work")
    async def label_work(
        actor: ConsoleActor = Depends(require_any_permission("ai:task:label", "ai:label:approve"))
    ):
        return {"success": True, "member_id": actor.member_id}

    @app.post("/test/csrf-write", dependencies=[Depends(require_same_origin_write)])
    async def csrf_write():
        return {"success": True, "written": True}

    @app.get("/test/cookie/login")
    async def cookie_login(response: Response):
        set_session_cookie(response, "test-session-token-xyz")
        set_flow_cookie(response, "test-flow-token-abc")
        return {"success": True}

    @app.get("/test/cookie/logout")
    async def cookie_logout(response: Response):
        clear_session_cookie(response)
        clear_flow_cookie(response)
        return {"success": True}

    return app


class ConsoleApiAccessGuardRegressionTest(unittest.TestCase):
    def setUp(self):
        self.app = _build_test_app()
        self.client = TestClient(self.app)

    def _make_session(self, member_id: str, roles: tuple[str, ...], fresh_step_up: bool = False) -> ConsoleSession:
        return ConsoleSession(
            session_id=f"sess-{member_id}",
            actor=ConsoleActor(member_id=member_id, roles=frozenset(roles)),
            email=f"{member_id}@iplms.internal",
            display_name=f"Member {member_id}",
            mfa_done=True,
            totp_enabled=True,
            step_up_at=datetime.now(timezone.utc) if fresh_step_up else None,
            totp_secret_set=True,
        )

    def test_require_permission_grants_access_for_authorized_role(self):
        session = self._make_session("m-analyst", ("ai_analyst",))
        with patch.object(auth_service, "resolve", return_value=session):
            res = self.client.get(
                "/test/metrics",
                headers={"Cookie": f"{SESSION_COOKIE}=valid-analyst-token"},
            )
            self.assertEqual(200, res.status_code)
            body = res.json()
            self.assertTrue(body["success"])
            self.assertEqual("m-analyst", body["member_id"])
            self.assertEqual(["ai_analyst"], body["roles"])

    def test_require_permission_denies_unauthorized_role_with_403(self):
        # Annotator không có quyền 'ai:metrics:read' -> Bị chặn 403 FORBIDDEN
        session = self._make_session("m-annotator", ("ai_annotator",))
        with patch.object(auth_service, "resolve", return_value=session):
            res = self.client.get(
                "/test/metrics",
                headers={"Cookie": f"{SESSION_COOKIE}=valid-annotator-token"},
            )
            self.assertEqual(403, res.status_code)
            body = res.json()
            self.assertFalse(body["success"])
            self.assertEqual("FORBIDDEN", body["code"])

    def test_require_permission_returns_401_when_session_missing_or_invalid(self):
        def _no_session(*_, **__):
            raise ConsoleAuthError("Phiên đã hết hạn, vui lòng đăng nhập lại.", "NO_SESSION")

        with patch.object(auth_service, "resolve", side_effect=_no_session):
            res = self.client.get("/test/metrics")
            self.assertEqual(401, res.status_code)
            body = res.json()
            self.assertFalse(body["success"])
            self.assertEqual("NO_SESSION", body["code"])

    def test_require_permission_raises_value_error_on_unknown_permission(self):
        with self.assertRaises(ValueError) as ctx:
            require_permission("ai:unknown:perm")
        self.assertIn("Quyền console không tồn tại", str(ctx.exception))

    def test_require_any_permission_allows_actor_with_at_least_one_permission(self):
        annotator_sess = self._make_session("m-annotator", ("ai_annotator",))
        reviewer_sess = self._make_session("m-reviewer", ("ai_reviewer",))

        # Annotator có 'ai:task:label'
        with patch.object(auth_service, "resolve", return_value=annotator_sess):
            res = self.client.get(
                "/test/label-work",
                headers={"Cookie": f"{SESSION_COOKIE}=annotator-token"},
            )
            self.assertEqual(200, res.status_code)

        # Reviewer có 'ai:label:approve'
        with patch.object(auth_service, "resolve", return_value=reviewer_sess):
            res = self.client.get(
                "/test/label-work",
                headers={"Cookie": f"{SESSION_COOKIE}=reviewer-token"},
            )
            self.assertEqual(200, res.status_code)

    def test_require_any_permission_denies_actor_with_none_of_permissions(self):
        analyst_sess = self._make_session("m-analyst", ("ai_analyst",))
        with patch.object(auth_service, "resolve", return_value=analyst_sess):
            res = self.client.get(
                "/test/label-work",
                headers={"Cookie": f"{SESSION_COOKIE}=analyst-token"},
            )
            self.assertEqual(403, res.status_code)
            self.assertEqual("FORBIDDEN", res.json()["code"])

    def test_require_any_permission_rejects_unknown_permission_at_definition(self):
        with self.assertRaises(ValueError) as ctx:
            require_any_permission("ai:invalid:perm")
        self.assertIn("Quyền console không tồn tại", str(ctx.exception))

    def test_authorize_any_rejects_step_up_permissions(self):
        import asyncio

        with patch.object(auth_service, "resolve", return_value=self._make_session("m-1", ("ai_lead",))):
            with self.assertRaises(ValueError) as ctx:
                asyncio.run(auth_service.authorize_any("token", ("ai:golden:freeze",)))
            self.assertIn("step-up", str(ctx.exception))

    def test_csrf_safe_methods_bypass_csrf_header_check(self):
        # GET request không yêu cầu CSRF header
        res = self.client.get("/test/csrf-write")
        # Sẽ trả về 405 Method Not Allowed thay vì 403 CSRF denied
        self.assertEqual(405, res.status_code)

    def test_csrf_write_requires_x_console_request_header(self):
        # POST thiếu header CSRF -> 403 Forbidden
        res = self.client.post("/test/csrf-write")
        self.assertEqual(403, res.status_code)
        self.assertIn("Thiếu header X-Console-Request", res.json()["message"])

    def test_csrf_write_rejects_cross_site_origin(self):
        # POST có header nhưng sec-fetch-site là cross-site -> 403 Forbidden
        headers = {
            CSRF_HEADER: "1",
            "sec-fetch-site": "cross-site",
        }
        res = self.client.post("/test/csrf-write", headers=headers)
        self.assertEqual(403, res.status_code)
        self.assertIn("Chỉ nhận request cùng nguồn", res.json()["message"])

    def test_csrf_write_succeeds_with_valid_same_origin_header(self):
        headers = {
            CSRF_HEADER: "1",
            "sec-fetch-site": "same-origin",
        }
        res = self.client.post("/test/csrf-write", headers=headers)
        self.assertEqual(200, res.status_code)
        self.assertTrue(res.json()["written"])

    def test_step_up_permission_enforcement(self):
        # Lead có quyền 'ai:golden:freeze' nhưng chưa nhập TOTP step-up gần đây -> 401 STEP_UP_REQUIRED
        stale_sess = self._make_session("m-lead", ("ai_lead",), fresh_step_up=False)
        with patch.object(auth_service, "resolve", return_value=stale_sess):
            res = self.client.post(
                "/test/golden/freeze",
                headers={
                    "Cookie": f"{SESSION_COOKIE}=lead-token",
                    CSRF_HEADER: "1",
                },
            )
            self.assertEqual(401, res.status_code)
            self.assertEqual("STEP_UP_REQUIRED", res.json()["code"])

        # Lead đã qua TOTP step-up gần đây -> Thành công 200 OK
        fresh_sess = self._make_session("m-lead", ("ai_lead",), fresh_step_up=True)
        with patch.object(auth_service, "resolve", return_value=fresh_sess):
            res = self.client.post(
                "/test/golden/freeze",
                headers={
                    "Cookie": f"{SESSION_COOKIE}=lead-token",
                    CSRF_HEADER: "1",
                },
            )
            self.assertEqual(200, res.status_code)
            self.assertTrue(res.json()["success"])

    def test_cookie_helpers_set_and_clear_correctly(self):
        # Login endpoint: sets cookies
        login_res = self.client.get("/test/cookie/login")
        self.assertEqual(200, login_res.status_code)
        self.assertIn(SESSION_COOKIE, login_res.cookies)
        self.assertIn(FLOW_COOKIE, login_res.cookies)
        self.assertEqual("test-session-token-xyz", login_res.cookies[SESSION_COOKIE])
        self.assertEqual("test-flow-token-abc", login_res.cookies[FLOW_COOKIE])

        # Logout endpoint: deletes cookies
        logout_res = self.client.get("/test/cookie/logout")
        self.assertEqual(200, logout_res.status_code)
        raw_set_cookie = logout_res.headers.get("set-cookie", "")
        # Max-age=0 hoặc expires trong quá khứ được gửi để xoá cookie
        self.assertIn(SESSION_COOKIE, raw_set_cookie)
        self.assertIn(FLOW_COOKIE, raw_set_cookie)


if __name__ == "__main__":
    unittest.main()
