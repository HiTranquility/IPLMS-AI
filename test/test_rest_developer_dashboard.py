"""Offline REST regression tests: no env files, providers, model files or DB."""
import os
import unittest
from unittest.mock import AsyncMock, patch

# Settings classes are imported without constructing them. Disable every dotenv
# source before any singleton/logger constructs settings, and clear process env.
from app.config.base_config import BaseConfig
from app.config import get_config
for settings_type in BaseConfig.__subclasses__():
    settings_type.model_config["env_file"] = None
with patch.dict(os.environ, {}, clear=True):
    get_config.cache_clear()
    get_config()
    from app.main import app
from fastapi.testclient import TestClient
from app.api.rest import developer_access
from app.api.rest.routes import copilot_controller, knowledge_controller
from app.core.copilot.dtos.copilot_dto import CopilotAnswer
from app.core.enums import IngestStatus
from app.core.knowledge.dtos.knowledge_dto import IngestResult
from app.core.exceptions import RagPipelineError


class DeveloperDashboardTests(unittest.TestCase):
    def setUp(self):
        developer_access._calls.clear()
        self.config = get_config()
        self.original = self.config.server.developer_dashboard_enabled
        self.config.server.developer_dashboard_enabled = True
        self.client = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 42000), raise_server_exceptions=False)

    def tearDown(self):
        self.config.server.developer_dashboard_enabled = self.original

    def test_disabled_dashboard_and_static_and_routes_are_inaccessible(self):
        self.config.server.developer_dashboard_enabled = False
        for path in ("/", "/dashboard", "/ui", "/static/index.html", "/static/INDEX.HTML", "/static/../static/index.html", "/api/system/info", "/system/info"):
            self.assertEqual(404, self.client.get(path).status_code, path)
        self.assertEqual(200, self.client.get("/health").status_code)
        self.assertEqual(200, self.client.get("/api/health").status_code)
        self.assertEqual(404, self.client.post("/api/copilot/ask", json={"query":"test"}).status_code)
        self.assertEqual(404, self.client.post("/api/knowledge/ingest").status_code)
        self.assertEqual(404, self.client.post("/api/vision/recognize").status_code)

    def test_gate_rejects_remote_host_peer_origin_and_forwarded(self):
        for headers in ({"host":"evil.example"}, {"origin":"https://evil.example"}, {"x-forwarded-for":"127.0.0.1"}, {"sec-fetch-site":"cross-site"}):
            self.assertEqual(403, self.client.get("/api/system/info", headers=headers).status_code)
        remote = TestClient(app, base_url="http://localhost", client=("192.0.2.1",42000))
        self.assertEqual(403, remote.get("/dashboard").status_code)

    def test_dashboard_self_contained_and_forecast_aliases_preserved(self):
        page = self.client.get("/dashboard")
        self.assertEqual(200, page.status_code)
        self.assertNotIn('src="https://', page.text)
        self.assertNotIn('innerHTML', page.text)
        self.assertIn("frame-ancestors 'none'", page.headers["content-security-policy"])
        paths = set(app.openapi()["paths"])
        for prefix in ("", "/api"):
            for route in ("/v1/ai/forecast/occupancy/{area_id}", "/forecast/occupancy/{area_id}", "/v1/ai/forecast/surge/{area_id}", "/forecast/surge/{area_id}"):
                self.assertIn(prefix + route, paths)
        self.assertNotIn("/api/forecast/simulate", paths)
        self.assertNotIn("/api/copilot/dispute-workflow/simulate", paths)

    def test_copilot_uses_guarded_service_without_seed_or_key_override(self):
        answer = CopilotAnswer(answer="Grounded",sources=["policy.md"],confidence=0.5)
        mock = AsyncMock(return_value=answer)
        with patch.object(copilot_controller.copilot_service, "ask_question", mock):
            response = self.client.post("/api/copilot/ask",json={"query":"policy?","parking_lot_id":"lot-a"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("Grounded",response.json()["data"][0]["answer"])
        self.assertFalse(mock.call_args.args[0].preview)
        self.assertEqual("lot-a",mock.call_args.args[0].parking_lot_id)
        self.assertEqual(422,self.client.post("/api/copilot/ask",json={"query":"q","api_key_override":"forbidden"}).status_code)
        self.assertEqual(422,self.client.post("/api/copilot/ask",json={"query":"x"*2001}).status_code)

    def test_copilot_failure_stays_failure_without_seed_fallback(self):
        with patch.object(copilot_controller.copilot_service,"ask_question",AsyncMock(side_effect=RagPipelineError("Unavailable"))):
            response=self.client.post("/api/copilot/ask",json={"query":"policy?"})
        self.assertEqual(422,response.status_code)
        self.assertFalse(response.json()["success"])

    def test_cost_limit(self):
        with patch.object(copilot_controller.copilot_service,"ask_question",AsyncMock(return_value=CopilotAnswer(answer="text",sources=[],confidence=0))):
            for _ in range(20):
                self.assertEqual(200,self.client.post("/api/copilot/ask",json={"query":"q"}).status_code)
            self.assertEqual(429,self.client.post("/api/copilot/ask",json={"query":"q"}).status_code)

    def _ingest(self):
        return self.client.post("/api/knowledge/ingest",data={"document_id":"d7e1375c-2cce-4a15-bd19-8ed62f9be944"},files={"file":("policy.txt",b"policy","text/plain")})

    def test_ingest_maps_seconds_and_reuses_document_id(self):
        result=IngestResult(document_id="doc",status=IngestStatus.SUCCESS,chunk_count=3,process_time=0.125,version_id="v1",version_no=1)
        mock=AsyncMock(return_value=result)
        with patch.object(knowledge_controller.ingestion_service,"ingest",mock):
            response=self._ingest(); self._ingest()
        self.assertEqual(200,response.status_code)
        self.assertTrue(response.json()["success"])
        self.assertEqual(125,response.json()["data"][0]["duration_ms"])
        self.assertEqual(mock.call_args_list[0].args[0].document_id,mock.call_args_list[1].args[0].document_id)

    def test_ingest_domain_failure_is_not_success(self):
        for status, code in ((IngestStatus.NO_TEXT_LAYER,422),(IngestStatus.EMBEDDING_FAILED,503)):
            with patch.object(knowledge_controller.ingestion_service,"ingest",AsyncMock(return_value=IngestResult(document_id="doc",status=status,message="Rejected"))):
                response=self._ingest()
            self.assertEqual(code,response.status_code)
            self.assertFalse(response.json()["success"])
            self.assertEqual(status.value,response.json()["data"][0]["status"])

    def test_ingest_requires_document_key_and_bounds_upload(self):
        self.assertEqual(422,self.client.post("/api/knowledge/ingest",files={"file":("a.txt",b"a")}).status_code)
        with patch.object(knowledge_controller,"KNOWLEDGE_MAX_FILE_BYTES",2), patch.object(knowledge_controller.ingestion_service,"ingest",AsyncMock()) as mock:
            self.assertEqual(413,self._ingest().status_code)
            mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
