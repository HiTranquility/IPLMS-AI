"""Config đọc từ biến môi trường — chỗ hay lệch tên nhất giữa code và manifest."""
import unittest

from app.config import get_config
from app.config.datalake_config import DatalakeConfig
from app.config.vision_config import VisionConfig


class VisionConfigTest(unittest.TestCase):
    def test_tach_danh_sach_ngon_ngu_ocr(self):
        cfg = VisionConfig(ocr_languages="en,vi")
        self.assertEqual(cfg.ocr_language_list, ["en", "vi"])

    def test_bo_khoang_trang_thua_va_phan_tu_rong(self):
        cfg = VisionConfig(ocr_languages=" en , , vi ")
        self.assertEqual(cfg.ocr_language_list, ["en", "vi"])

    def test_tach_nhan_loai_xe(self):
        cfg = VisionConfig(vehicle_labels="car_sedan,car_suv,motorbike,truck")
        self.assertEqual(len(cfg.vehicle_label_list), 4)
        self.assertIn("motorbike", cfg.vehicle_label_list)

    def test_so_nhan_khop_so_lop_cua_model(self):
        """Lệch nhau thì classify_vehicle trả sai nhãn hoặc ném IndexError."""
        cfg = get_config().vision
        self.assertEqual(len(cfg.vehicle_label_list), cfg.vehicle_num_classes)

    def test_model_artifact_defaults_co_version(self):
        cfg = VisionConfig()
        self.assertEqual(cfg.yolo_model_version, "bootstrap-v1")
        self.assertEqual(cfg.vehicle_model_version, "v1")

    def test_production_warmup_is_safe_by_default(self):
        self.assertTrue(VisionConfig().vision_warmup_on_start)

    def test_onnx_config_defaults(self):
        cfg = VisionConfig()
        self.assertTrue(cfg.onnx_enabled)
        self.assertEqual(cfg.onnx_model_dir, "data/models")


class ArtifactConfigTest(unittest.TestCase):
    def test_gioi_han_dung_luong_doi_sang_bytes(self):
        config = get_config().object_storage
        self.assertEqual(config.max_artifact_bytes, config.max_artifact_mb * 1024 * 1024)


class DatalakeConfigTest(unittest.TestCase):
    def test_export_batch_and_occupancy_slot_are_positive(self):
        config = get_config().datalake
        self.assertGreater(config.export_batch_size, 0)
        self.assertGreater(config.occupancy_slot_minutes, 0)

    def test_operational_database_is_not_implicitly_the_copilot_database(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_DATALAKE_SOURCE_DATABASE_URL", None)
            config = DatalakeConfig(_env_file=None)
            self.assertEqual(config.source_database_url, "")


class WorkflowConfigTest(unittest.TestCase):
    def test_workflow_mac_dinh_tat_va_dung_memory_cho_local(self):
        config = get_config().workflow
        self.assertFalse(config.enabled)
        self.assertEqual(config.checkpoint_backend, "memory")
        self.assertEqual(config.checkpoint_schema, "ai_workflow")
        self.assertGreater(config.checkpoint_retention_days, 0)
        self.assertGreater(config.checkpoint_retention_batch_size, 0)


class ServerConfigTest(unittest.TestCase):
    def test_max_message_khop_10mb_mac_dinh(self):
        """Phải khớp AI_GRPC_MAX_MESSAGE_MB=10 bên NestJS, lệch là RESOURCE_EXHAUSTED."""
        self.assertEqual(get_config().server.grpc_max_message_length, 10 * 1024 * 1024)

    def test_config_duoc_cache(self):
        self.assertIs(get_config(), get_config())


if __name__ == "__main__":
    unittest.main()
