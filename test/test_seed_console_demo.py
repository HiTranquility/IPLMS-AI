"""Kiểm thử script nạp dữ liệu mẫu seed_console_demo.py (A-7, A-70, A-71)."""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.infra.database.console_vision_store import ConsoleVisionStore
from app.script.seed_console_demo import check_environment, seed_vision_pipeline


class SeedEnvironmentGuardTest(unittest.TestCase):
    def test_chan_production_va_khi_tat_co_demo_seed(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "Production"):
                check_environment()

        fake_cfg = SimpleNamespace(console=SimpleNamespace(demo_seed_enabled=False))
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False):
            with patch("app.script.seed_console_demo.get_config", return_value=fake_cfg):
                with self.assertRaisesRegex(RuntimeError, "AI_CONSOLE_DEMO_SEED_ENABLED"):
                    check_environment()

    def test_seed_vision_pipeline_chi_de_xuat_model_va_policy_khong_bia_so_lieu(self):
        """A-7 / A-70 / A-71: kiểm hành vi seed_vision_pipeline chỉ gọi propose kèm nhãn [DEMO]."""
        vstore = AsyncMock()
        vstore.db_url = "postgresql://local/test"
        vstore.list_snapshots.return_value = [
            {"id": "snap-golden-1", "kind": "golden", "frozen_at": "2026-10-25T00:00:00Z"},
            {"id": "snap-train-1", "kind": "train", "frozen_at": None},
        ]
        vstore.list_models.return_value = []
        vstore.list_policies.return_value = []

        fake_conn = MagicMock()
        with (
            patch("app.script.seed_console_demo.connect_with_fallback", return_value=(fake_conn, "postgresql://local/test")),
            patch("app.script.seed_console_demo.generate_plate_image", return_value=b"fake-png"),
            patch("app.script.seed_console_demo.VisionLabService") as MockLab,
            patch("app.script.seed_console_demo.ModelLabService") as MockModelSvc,
            patch("app.script.seed_console_demo.AcceptPolicyService") as MockPolicySvc,
        ):
            lab = MockLab.return_value
            lab.add_label = AsyncMock(return_value="lbl-1")
            lab.decide = AsyncMock()
            lab.seed_demo_samples = AsyncMock(return_value={"seeded_samples": 5, "seeded_reviews": 2})

            models_svc = MockModelSvc.return_value
            models_svc.register = AsyncMock(return_value="model-1")
            models_svc.start_eval = AsyncMock(return_value="run-1")
            models_svc.drain = AsyncMock()
            models_svc.propose = AsyncMock()
            models_svc.promote = AsyncMock()

            policy_svc = MockPolicySvc.return_value
            policy_svc.propose = AsyncMock(return_value={"id": "pol-1", "version": 1})
            policy_svc.decide = AsyncMock()

            asyncio.run(seed_vision_pipeline(vision_store=vstore))

            models_svc.register.assert_awaited_once()
            reg_payload = models_svc.register.call_args.args[1]
            self.assertIn("[DEMO]", reg_payload["note"])
            models_svc.propose.assert_awaited_once()
            self.assertIn("[DEMO]", models_svc.propose.call_args.args[2])
            models_svc.promote.assert_not_called()

            policy_svc.propose.assert_awaited_once()
            policy_reason = policy_svc.propose.call_args.args[3]
            self.assertIn("[DEMO]", policy_reason)
            self.assertNotIn("100% mẫu", policy_reason)
            policy_svc.decide.assert_not_called()


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class SeedVisionPipelineDbTest(unittest.TestCase):
    def setUp(self):
        import psycopg2
        from psycopg2 import sql

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        self.schema = "seed_demo_" + uuid4().hex
        self.admin_conn = psycopg2.connect(base_url)
        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        sep = "&" if "?" in base_url else "?"
        self.url = f"{base_url}{sep}options=-csearch_path%3D{self.schema}"
        self.vstore = ConsoleVisionStore(self.url)

    def tearDown(self):
        from psycopg2 import sql

        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin_conn.close()

    def test_seed_vision_pipeline_trung_thuc_khong_tu_promote_hay_bia_so_lieu(self):
        """A-7 / A-70 / A-71: chạy seed trên DB test thật, model và policy chỉ đề xuất kèm nhãn [DEMO]."""
        asyncio.run(seed_vision_pipeline(vision_store=self.vstore))

        snaps = asyncio.run(self.vstore.list_snapshots())
        kinds = {s["kind"]: s for s in snaps}
        self.assertIn("golden", kinds)
        self.assertIsNotNone(kinds["golden"]["frozen_at"])
        self.assertIn("train", kinds)

        models = asyncio.run(self.vstore.list_models())
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["stage"], "proposed")
        self.assertIn("[DEMO]", models[0]["note"])

        evals = asyncio.run(self.vstore.list_evals())
        self.assertEqual(len(evals), 1)
        self.assertEqual(evals[0]["status"], "DONE")

        policies = asyncio.run(self.vstore.list_policies())
        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0]["status"], "PROPOSED")
        self.assertIn("[DEMO]", policies[0]["reason"])
        self.assertNotIn("100% mẫu", policies[0]["reason"])


if __name__ == "__main__":
    unittest.main()
