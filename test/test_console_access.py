"""Ma trận vai trò × quyền của AI Console phải khớp PROB-049 §3 / ADR-0048."""
import unittest

from app.core.console.dtos import ConsoleActor
from app.core.console.engines import access_policy as policy
from app.core.exceptions import ConsoleAccessDenied

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


if __name__ == "__main__":
    unittest.main()
