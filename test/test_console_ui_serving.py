"""console_main phục vụ bản build `ai/ui`: SPA fallback, chặn đọc ra ngoài dist, API sai trả JSON."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ConsoleUiServingTest(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient

        from app import console_main

        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        dist = root / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<div id=root></div>", encoding="utf-8")
        (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
        (root / "secret.txt").write_text("không được lộ", encoding="utf-8")
        self.patch = patch.object(console_main, "UI_DIST", dist.resolve())
        self.patch.start()
        self.client = TestClient(console_main.app)

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_route_phia_client_tra_index_kem_csp(self):
        r = self.client.get("/console/copilot")
        self.assertEqual(200, r.status_code)
        self.assertIn("id=root", r.text)
        self.assertIn("script-src 'self'", r.headers["content-security-policy"])
        self.assertEqual(200, self.client.get("/console/assets/app.js").status_code)

    def test_khong_doc_file_ngoai_dist(self):
        r = self.client.get("/console/..%2Fsecret.txt")
        self.assertNotIn("không được lộ", r.text)

    def test_api_sai_tra_json_404_khong_tra_spa(self):
        r = self.client.get("/console/api/khong-co")
        self.assertEqual((404, "NOT_FOUND"), (r.status_code, r.json()["code"]))

    def test_chua_build_thi_bao_ro(self):
        with patch("app.console_main.UI_DIST", Path(self.tmp.name) / "missing"):
            r = self.client.get("/console/")
        self.assertEqual(503, r.status_code)
        self.assertIn("pnpm --dir ui build", r.text)


if __name__ == "__main__":
    unittest.main()
