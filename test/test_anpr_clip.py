"""Đọc biển số từ clip (IPLMS REQ-021 A): F1 giới hạn, F2 gộp theo xe, F3 trường sự kiện, F7 không lưu clip."""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_config
from app.core.console.dtos import ConsoleActor
from app.core.console.services.tools_service import ToolsService
from app.core.exceptions import ConsoleAccessDenied
from app.core.vision import AnprService
from app.core.vision.engines.anpr.video import ClipLimits, PlateRead, analyze_clip, group_reads
from test.clip_fixtures import CARS, build_clip, fake_recognizer

ML = ConsoleActor("m-ml", frozenset({"ai_ml_engineer"}))
ANALYST = ConsoleActor("m-an", frozenset({"ai_analyst"}))
LIMITS = ClipLimits(max_duration_s=60, max_frames=240, sample_interval_s=0.5)
BOX = (100, 300, 320, 380)


def _read(t, plate, bbox=BOX, conf=0.9):
    return PlateRead(t, plate, conf, bbox, plate.encode())


class _IsolatedTempDir(unittest.TestCase):
    """Đổi thư mục tạm của tiến trình sang một thư mục riêng để kiểm không còn file nào sót (F7)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="clip-test-")
        patcher = patch.object(tempfile, "tempdir", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def assertNoClipLeft(self):
        self.assertEqual([], os.listdir(self.tmp))


class GroupReadsTest(unittest.TestCase):
    def test_cung_xe_doc_lech_mot_ky_tu_van_mot_su_kien_nho_iou(self):
        reads = [_read(0.0, "51A-888.88"), _read(0.5, "51A-888.80"), _read(1.0, "51A-888.88")]
        events = group_reads(reads, iou_threshold=0.3, max_gap_s=1.5)
        self.assertEqual(1, len(events))
        self.assertEqual("51A-888.88", events[0].summary()["plate_number"])

    def test_hai_xe_cung_cho_cach_nhau_qua_lau_la_hai_su_kien(self):
        reads = [_read(0.0, "51A-888.88"), _read(5.0, "30E-123.45")]
        self.assertEqual(2, len(group_reads(reads, 0.3, 1.5)))

    def test_cung_bien_nhung_khac_vi_tri_van_gop_theo_plate_key(self):
        reads = [_read(0.0, "51A-888.88", (0, 0, 10, 10)), _read(0.5, "51A88888", (500, 500, 510, 510))]
        self.assertEqual(1, len(group_reads(reads, 0.3, 1.5)))

    def test_hai_xe_cung_luc_khac_vi_tri_khac_bien_la_hai_su_kien(self):
        reads = [_read(0.0, "51A-888.88", (0, 0, 100, 40)), _read(0.0, "30E-123.45", (600, 0, 700, 40)),
                 _read(0.5, "51A-888.88", (10, 0, 110, 40)), _read(0.5, "30E-123.45", (610, 0, 710, 40))]
        self.assertEqual(2, len(group_reads(reads, 0.3, 1.5)))


class AnalyzeClipTest(_IsolatedTempDir):
    def test_clip_mau_3_xe_ra_dung_3_su_kien_du_truong(self):
        clip = build_clip()
        result = analyze_clip(clip, ".mp4", LIMITS, fake_recognizer(misread_every=3), 0.3, 1.5)
        events = result["events"]
        self.assertEqual([plate for plate, _ in CARS], [e["plate_number"] for e in events])
        for event in events:
            # F3: biển, mốc giây, ảnh frame tốt nhất, độ tin cậy.
            self.assertEqual({"plate_number", "confidence", "best_time_s", "start_time_s", "end_time_s",
                              "frame_count", "crop_bytes"}, set(event))
            self.assertGreater(event["frame_count"], 1)
            self.assertLessEqual(event["start_time_s"], event["best_time_s"])
            self.assertLessEqual(event["best_time_s"], event["end_time_s"])
            self.assertTrue(event["crop_bytes"].startswith(b"crop-"))
        # Xe sau vào sau khi xe trước đã ra hẳn (3 s chạy + 2 s nghỉ).
        self.assertTrue(events[0]["end_time_s"] < events[1]["start_time_s"] < events[2]["start_time_s"])
        self.assertNoClipLeft()

    def test_webm_cung_doc_duoc(self):
        result = analyze_clip(build_clip(suffix=".webm"), ".webm", LIMITS, fake_recognizer(), 0.3, 1.5)
        self.assertEqual(3, len(result["events"]))
        self.assertNoClipLeft()

    def test_che_do_chuyen_dong_bo_frame_dung_yen(self):
        clip = build_clip()
        by_interval = analyze_clip(clip, ".mp4", LIMITS, fake_recognizer(), 0.3, 1.5)
        motion = ClipLimits(max_duration_s=60, max_frames=240, sample_interval_s=0.5, motion_threshold=0.01)
        by_motion = analyze_clip(clip, ".mp4", motion, fake_recognizer(), 0.3, 1.5)
        self.assertLess(by_motion["sampled_frames"], by_interval["sampled_frames"])
        self.assertEqual(3, len(by_motion["events"]))

    def test_clip_dai_qua_gioi_han_bi_tu_choi_va_khong_de_lai_file(self):
        short = ClipLimits(max_duration_s=5, max_frames=240, sample_interval_s=0.5)
        with self.assertRaisesRegex(ValueError, "vượt giới hạn"):
            analyze_clip(build_clip(), ".mp4", short, fake_recognizer(), 0.3, 1.5)
        self.assertNoClipLeft()

    def test_engine_loi_giua_chung_van_xoa_file_tam(self):
        def boom(_):
            raise RuntimeError("engine hỏng")

        with self.assertRaises(RuntimeError):
            analyze_clip(build_clip(), ".mp4", LIMITS, boom, 0.3, 1.5)
        self.assertNoClipLeft()

    def test_file_khong_phai_video_bi_tu_choi(self):
        with self.assertRaisesRegex(ValueError, "Không đọc được clip"):
            analyze_clip(b"not a video" * 100, ".mp4", LIMITS, fake_recognizer(), 0.3, 1.5)
        self.assertNoClipLeft()


class RecognizeClipServiceTest(_IsolatedTempDir):
    """F1 ở tầng service: định dạng và dung lượng đọc từ config."""

    def setUp(self):
        super().setUp()
        get_config.cache_clear()
        self.addCleanup(get_config.cache_clear)

    def test_sai_dinh_dang_rong_va_qua_dung_luong(self):
        with self.assertRaisesRegex(ValueError, "MP4 hoặc WebM"):
            AnprService.recognize_clip(b"x", "image/png")
        with self.assertRaisesRegex(ValueError, "rỗng"):
            AnprService.recognize_clip(b"", "video/mp4")
        with patch.dict(os.environ, {"AI_CLIP_MAX_BYTES": "1000"}):
            get_config.cache_clear()
            with self.assertRaisesRegex(ValueError, "vượt"):
                AnprService.recognize_clip(b"x" * 1001, "video/mp4")

    def test_do_dai_doc_tu_config(self):
        with patch.dict(os.environ, {"AI_CLIP_MAX_DURATION_S": "4"}):
            get_config.cache_clear()
            with patch("app.core.vision.engines.anpr.engine.run_anpr", fake_recognizer()):
                with self.assertRaisesRegex(ValueError, "4 giây"):
                    AnprService.recognize_clip(build_clip(), "video/mp4")
        self.assertNoClipLeft()

    def test_clip_hop_le_duoc_nhan(self):
        with patch("app.core.vision.engines.anpr.engine.run_anpr", fake_recognizer()):
            result = AnprService.recognize_clip(build_clip(), "video/mp4; codecs=avc1")
        self.assertEqual(3, len(result["events"]))
        self.assertNoClipLeft()


@unittest.skipUnless(os.getenv("AI_TEST_REAL_ANPR"), "requires AI_TEST_REAL_ANPR=1 (YOLO + EasyOCR nạp được, ~40 s CPU)")
class RealEngineClipTest(_IsolatedTempDir):
    """Clip mẫu 3 xe qua `run_anpr` thật — tiêu chí F2 của REQ-021 trên bộ clip tổng hợp."""

    def test_clip_mau_3_xe_qua_engine_that(self):
        from app.core.vision.engines.anpr.engine import run_anpr

        motion = ClipLimits(max_duration_s=60, max_frames=240, sample_interval_s=0.5, motion_threshold=0.01)
        result = analyze_clip(build_clip(), ".mp4", motion, run_anpr, 0.3, 1.5)
        self.assertEqual([plate for plate, _ in CARS], [e["plate_number"] for e in result["events"]])
        self.assertNoClipLeft()


class ConsoleClipTest(unittest.IsolatedAsyncioTestCase):
    async def test_can_quyen_va_tra_anh_crop_base64(self):
        svc = ToolsService(store=None, copilot=None, ingestion=None)
        with self.assertRaises(ConsoleAccessDenied):
            await svc.try_anpr_clip(ANALYST, b"x", "video/mp4")
        fake = {"sampled_frames": 2, "plate_reads": 2, "events": [
            {"plate_number": "51A-888.88", "confidence": 0.9, "best_time_s": 1.0, "start_time_s": 0.5,
             "end_time_s": 1.5, "frame_count": 2, "crop_bytes": b"\xff\xd8jpeg"}]}
        with patch.object(AnprService, "recognize_clip", return_value=fake) as call:
            out = await svc.try_anpr_clip(ML, b"clip", "video/mp4", True)
        call.assert_called_once_with(b"clip", "video/mp4", True)
        event = out["events"][0]
        self.assertNotIn("crop_bytes", event)
        self.assertTrue(event["crop_image"].startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()
