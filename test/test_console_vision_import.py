"""Kênh A2 backend → AI Console (IPLMS ADR-0048 §5): watermark, ảnh, chặn id dạng rõ."""
import asyncio
import hashlib
import io
import os
import unittest
import urllib.error
from uuid import uuid4

from app.core.console.dtos import ExportedCapture
from app.core.console.services.vision_import_service import ConsoleVisionImportService

IMG = b"\xff\xd8 crop bytes"
SHA = hashlib.sha256(IMG).hexdigest()
REF = "b" * 64


def capture(updated_at="2026-10-16T01:00:00+00:00", capture_id=None, **kw):
    data = dict(
        capture_id=capture_id or str(uuid4()), image_url="http://storage/x.jpg", image_sha256=SHA,
        machine_plate="51A12345", machine_confidence=0.91, confirmed_plate="51A12345",
        human_corrected=False, selection_reasons=("random_audit",), status="PENDING", purpose="train",
        final_plate="", group_ref=REF, area_ref=REF, updated_at=updated_at, captured_at=updated_at,
    )
    data.update(kw)
    return ExportedCapture(**data)


class FakeStore:
    def __init__(self):
        self.cursor = None
        self.samples, self.crops, self.errors = {}, {}, []

    async def import_watermark(self):
        return (self.cursor[0].isoformat(), self.cursor[1]) if self.cursor else None

    async def existing_crops(self, ids):
        return {i for i in ids if i in self.crops}

    async def import_batch(self, samples, crops, rejects, cursor, retention_days):
        for s in samples:
            self.samples[s["capture_id"]] = s
        self.crops.update(crops)
        self.errors += rejects
        if cursor is not None:
            self.cursor = cursor


def service(fetch=lambda url: IMG):
    store = FakeStore()
    return ConsoleVisionImportService(store=store, fetch=fetch, retention_days=90), store


class VisionImportTest(unittest.TestCase):
    def test_luot_rong_chi_tra_watermark(self):
        svc, _ = service()
        self.assertEqual("", asyncio.run(svc.import_batch([]))["watermark_at"])

    def test_watermark_la_mau_moi_nhat_ke_ca_khi_gui_lon_xon(self):
        svc, store = service()
        late = capture("2026-10-16T03:00:00+00:00")
        early = capture("2026-10-16T01:00:00+00:00")
        result = asyncio.run(svc.import_batch([late, early]))
        self.assertEqual((2, late.capture_id), (result["accepted"], result["watermark_id"]))
        self.assertTrue(result["watermark_at"].startswith("2026-10-16T03:00:00"))
        # Gửi lại mẫu cũ không kéo watermark lùi.
        result = asyncio.run(svc.import_batch([early]))
        self.assertEqual(late.capture_id, result["watermark_id"])

    def test_sha256_lech_bi_loai_va_con_tro_van_di_tiep(self):
        svc, store = service(fetch=lambda url: b"anh khac")
        bad = capture()
        result = asyncio.run(svc.import_batch([bad]))
        self.assertEqual((0, [bad.capture_id]), (result["accepted"], result["rejected_ids"]))
        self.assertEqual(bad.capture_id, result["watermark_id"])  # lỗi vĩnh viễn: không gửi lại mãi
        self.assertNotIn(bad.capture_id, store.samples)

    def test_loi_tam_dung_con_tro_truoc_mau_loi_de_backend_gui_lai(self):
        calls = {"n": 0}

        def flaky(url):
            calls["n"] += 1
            if calls["n"] == 2:
                raise urllib.error.URLError("storage down")
            return IMG

        svc, store = service(fetch=flaky)
        first = capture("2026-10-16T01:00:00+00:00")
        second = capture("2026-10-16T02:00:00+00:00")
        third = capture("2026-10-16T03:00:00+00:00")
        result = asyncio.run(svc.import_batch([first, second, third]))
        self.assertEqual(first.capture_id, result["watermark_id"])
        self.assertIn(third.capture_id, store.samples)  # vẫn lưu, gửi lại sẽ là upsert

    def test_storage_404_la_loi_vinh_vien(self):
        def gone(url):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())

        svc, _ = service(fetch=gone)
        sample = capture()
        self.assertEqual(sample.capture_id, asyncio.run(svc.import_batch([sample]))["watermark_id"])

    def test_chan_id_dang_ro_thay_cho_hmac(self):
        svc, _ = service()
        with self.assertRaisesRegex(ValueError, "HMAC"):
            asyncio.run(svc.import_batch([capture(area_ref=str(uuid4()))]))

    def test_tu_choi_lo_qua_lon_va_thoi_gian_thieu_mui_gio(self):
        svc, _ = service()
        with self.assertRaises(ValueError):
            asyncio.run(svc.import_batch([capture() for _ in range(201)]))
        with self.assertRaisesRegex(ValueError, "múi giờ"):
            asyncio.run(svc.import_batch([capture("2026-10-16T01:00:00")]))

    def test_mau_da_co_anh_khong_tai_lai(self):
        fetched = []
        svc, store = service(fetch=lambda url: fetched.append(url) or IMG)
        sample = capture()
        asyncio.run(svc.import_batch([sample]))
        asyncio.run(svc.import_batch([capture(capture_id=sample.capture_id, status="LABELED",
                                               final_plate="51A12345")]))
        self.assertEqual(1, len(fetched))
        self.assertEqual("LABELED", store.samples[sample.capture_id]["status"])


class VisionExportMapperTest(unittest.TestCase):
    def test_proto_sang_dto_va_nguoc_lai(self):
        from app.api.grpc.generated_stubs import get_stub
        from app.api.grpc.mappers.dataset_mapper import to_export_response, to_exported_captures

        pb2, _ = get_stub("dataset_service")
        request = pb2.ExportForConsoleRequest(samples=[pb2.ConsoleExportSample(
            capture_id="3F1C2A64-5B7D-4E8F-9A01-23456789ABCD", image_sha256=SHA.upper(),
            has_machine_confidence=False, status="PENDING", updated_at="2026-10-16T01:00:00Z",
        )])
        dto = to_exported_captures(request)[0]
        self.assertEqual("3f1c2a64-5b7d-4e8f-9a01-23456789abcd", dto.capture_id)
        self.assertIsNone(dto.machine_confidence)
        self.assertEqual("train", dto.purpose)
        response = to_export_response({"accepted": 1, "rejected": 0, "rejected_ids": [],
                                       "watermark_at": "t", "watermark_id": "i"})
        self.assertEqual(("t", "i"), (response.watermark_at, response.watermark_id))

    def test_nguong_da_duyet_sang_proto(self):
        from app.api.grpc.mappers.dataset_mapper import to_accept_policy_response

        self.assertFalse(to_accept_policy_response(None).found)
        reply = to_accept_policy_response({"id": "p1", "version": 3, "auto_accept_threshold": 0.88,
                                           "audit_rate": 0.05, "decided_at": "2026-10-17T01:00:00+00:00"})
        self.assertEqual((True, "p1", 3, 0.88, 0.05),
                         (reply.found, reply.policy_id, reply.version, reply.auto_accept_threshold, reply.audit_rate))


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class VisionImportStoreTest(unittest.TestCase):
    def setUp(self):
        import psycopg2
        from psycopg2 import sql

        from app.infra.database.console_vision_store import ConsoleVisionStore

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        self.schema = "vision_import_" + uuid4().hex
        self.admin_conn = psycopg2.connect(base_url)
        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        sep = "&" if "?" in base_url else "?"
        self.store = ConsoleVisionStore(f"{base_url}{sep}options=-csearch_path%3D{self.schema}")
        self.svc = ConsoleVisionImportService(store=self.store, fetch=lambda url: IMG, retention_days=90)

    def tearDown(self):
        from psycopg2 import sql

        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin_conn.close()

    def test_nhap_luu_anh_watermark_ben_qua_khoi_dong_lai(self):
        sample = capture("2026-10-16T01:00:00+00:00")
        result = asyncio.run(self.svc.import_batch([sample]))
        self.assertEqual(1, result["accepted"])
        self.assertEqual(IMG, asyncio.run(self.store.crop(sample.capture_id)))

        # Process khác (backend khởi động lại) hỏi lượt rỗng vẫn thấy đúng mốc.
        again = ConsoleVisionImportService(store=self.store, fetch=lambda url: IMG, retention_days=90)
        self.assertEqual(sample.capture_id, asyncio.run(again.import_batch([]))["watermark_id"])
        status = asyncio.run(self.store.import_status())
        self.assertEqual(1, status["sample_count"])


if __name__ == "__main__":
    unittest.main()
