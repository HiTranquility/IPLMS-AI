"""CORS của REST inference chỉ mở cho origin khai trong AI_CORS_ALLOW_ORIGINS (bug-045)."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rest.middlewares.cors import register_cors
from app.config.server_config import ServerConfig

EVIL = "https://evil.example"
UI = "http://localhost:5173"


def _client(origins: str) -> TestClient:
    config = SimpleNamespace(server=ServerConfig(cors_allow_origins=origins))
    app = FastAPI()
    with patch("app.api.rest.middlewares.cors.get_config", return_value=config):
        register_cors(app)

    @app.get("/api/forecast/x")
    def x():
        return {"ok": 1}

    return TestClient(app)


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/api/forecast/x",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


class CorsPolicyTest(unittest.TestCase):
    def test_mac_dinh_khong_phat_header_cors_cho_origin_la(self):
        client = _client("")
        self.assertIsNone(_preflight(client, EVIL).headers.get("access-control-allow-origin"))
        r = client.get("/api/forecast/x", headers={"Origin": EVIL, "Cookie": "a=b"})
        self.assertIsNone(r.headers.get("access-control-allow-origin"))

    def test_origin_trong_danh_sach_duoc_qua_va_khong_kem_credentials(self):
        client = _client(f"{UI}, http://127.0.0.1:5173")
        r = _preflight(client, UI)
        self.assertEqual(r.headers.get("access-control-allow-origin"), UI)
        self.assertIsNone(r.headers.get("access-control-allow-credentials"))

    def test_origin_ngoai_danh_sach_bi_tu_choi(self):
        client = _client(UI)
        r = _preflight(client, EVIL)
        self.assertNotEqual(r.headers.get("access-control-allow-origin"), EVIL)


if __name__ == "__main__":
    unittest.main()
