"""REST ANPR: trần byte, định dạng ảnh và không lộ chi tiết lỗi (bug-043)."""
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rest.routes.anpr_controller import router
from app.core.constants import ANPR_MAX_IMAGE_BYTES

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class AnprRestUploadTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router, prefix="/api")
        self.client = TestClient(app)
        self.seen = []

        async def fake_recognize(image_bytes, lane_id=None):
            self.seen.append(len(image_bytes))
            raise RuntimeError("/secret/path/model.pt not found")

        patcher = patch("app.core.vision.AnprService.recognize", side_effect=fake_recognize)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _post(self, data, name="x.jpg", content_type="image/jpeg"):
        return self.client.post("/api/anpr/recognize", files={"file": (name, data, content_type)})

    def test_anh_vuot_tran_tra_413_va_khong_toi_engine(self):
        r = self._post(JPEG + b"\x00" * ANPR_MAX_IMAGE_BYTES)
        self.assertEqual(r.status_code, 413)
        self.assertEqual(self.seen, [])

    def test_file_khong_phai_anh_tra_415_du_khai_image_jpeg(self):
        r = self._post(b"A" * 1024)
        self.assertEqual(r.status_code, 415)
        self.assertEqual(self.seen, [])

    def test_jpeg_va_png_hop_le_toi_engine(self):
        self._post(JPEG)
        self._post(PNG, name="x.png", content_type="image/png")
        self.assertEqual(self.seen, [len(JPEG), len(PNG)])

    def test_loi_engine_khong_lo_message_exception(self):
        body = self._post(JPEG).json()
        self.assertFalse(body["success"])
        self.assertNotIn("secret", body["message"])


if __name__ == "__main__":
    unittest.main()
