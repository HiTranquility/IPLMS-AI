import asyncio
import unittest

from app.core.console.dtos import ConsoleActor
from app.core.console.engines.demo_plate_generator import DEMO_SAMPLES, generate_plate_image
from app.core.exceptions import ConsoleAccessDenied


class DemoPlateGeneratorTest(unittest.TestCase):
    def test_generate_car_plate(self):
        b = generate_plate_image("51A-888.88", plate_type="car", two_line=False)
        self.assertIsInstance(b, bytes)
        self.assertTrue(len(b) > 1000)
        # JPEG SOI marker
        self.assertTrue(b.startswith(b"\xff\xd8"))

    def test_generate_moto_two_line_plate(self):
        b = generate_plate_image("29-B1 999.99", plate_type="moto", two_line=True)
        self.assertIsInstance(b, bytes)
        self.assertTrue(len(b) > 1000)
        self.assertTrue(b.startswith(b"\xff\xd8"))

    def test_generate_taxi_yellow_plate(self):
        b = generate_plate_image("30E-123.45", plate_type="taxi", two_line=False)
        self.assertIsInstance(b, bytes)
        self.assertTrue(len(b) > 1000)
        self.assertTrue(b.startswith(b"\xff\xd8"))


JPEG_SOI = bytes([0xFF, 0xD8])


class _Store:
    def __init__(self):
        self.calls = []

    async def seed_demo_samples(self, actor_id, samples, retention_days):
        self.calls.append((actor_id, samples))
        return {"seeded_samples": len(samples), "seeded_reviews": 0}


class SeedDemoGuardTest(unittest.TestCase):
    actor = ConsoleActor(member_id="m1", roles=frozenset({"ai_annotator"}))

    def _service(self, enabled):
        from app.core.console.services.vision_lab_service import ConsoleVisionLabService

        store = _Store()
        return ConsoleVisionLabService(store=store, demo_seed_enabled=enabled), store

    def test_tat_co_thi_khong_ghi_gi(self):
        service, store = self._service(False)
        with self.assertRaises(ConsoleAccessDenied):
            asyncio.run(service.seed_demo_samples(self.actor))
        self.assertEqual([], store.calls)

    def test_khong_truyen_co_thi_doc_config_mac_dinh_tat(self):
        import os
        from types import SimpleNamespace
        from unittest import mock

        from app.config.console_config import ConsoleConfig
        from app.core.console.services.vision_lab_service import ConsoleVisionLabService

        store = _Store()
        # get_config có cache và đọc .env.dev: dựng config sạch để đo đúng giá trị mặc định.
        env = {k: v for k, v in os.environ.items() if k != "AI_CONSOLE_DEMO_SEED_ENABLED"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = SimpleNamespace(console=ConsoleConfig(_env_file=None))
        with mock.patch("app.core.console.services.vision_lab_service.get_config", return_value=cfg):
            with self.assertRaises(ConsoleAccessDenied):
                asyncio.run(ConsoleVisionLabService(store=store).seed_demo_samples(self.actor))
        self.assertEqual([], store.calls)

    def test_bat_co_thi_service_dung_anh_va_hash(self):
        service, store = self._service(True)
        result = asyncio.run(service.seed_demo_samples(self.actor))
        self.assertEqual(len(DEMO_SAMPLES), result["seeded_samples"])
        [(actor_id, samples)] = store.calls
        self.assertEqual("m1", actor_id)
        self.assertTrue(all(s["image"].startswith(JPEG_SOI) and len(s["image_sha256"]) == 64 for s in samples))


if __name__ == "__main__":
    unittest.main()
