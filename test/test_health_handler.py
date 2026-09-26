"""ISSUE-013: health theo từng service — thiếu cấu hình LLM/embedding thì báo NOT_SERVING."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from app.api.grpc.generated_stubs import STUBS_READY, get_stub


@unittest.skipUnless(STUBS_READY, "Chưa sinh stub — chạy app/script/compile_proto.py")
class HealthHandlerTest(unittest.TestCase):
    def setUp(self):
        from app.api.grpc.handlers import health_handler

        self.module = health_handler
        self.pb2, _ = get_stub("health_service")
        self.status = self.pb2.HealthCheckResponse.ServingStatus

    def _check(self, service, key="", base_url="", embedding_url=""):
        config = SimpleNamespace(
            llm=SimpleNamespace(llm_api_key=key, llm_base_url=base_url),
            embedding=SimpleNamespace(base_url=embedding_url),
        )
        request = self.pb2.HealthCheckRequest(service=service)
        with mock.patch.object(self.module, "get_config", return_value=config):
            return asyncio.run(self.module.HealthHandler().Check(request, None)).status

    def test_whole_server_is_serving_even_without_llm(self):
        self.assertEqual(self.status.SERVING, self._check(""))

    def test_copilot_not_serving_without_key_or_base_url(self):
        self.assertEqual(self.status.NOT_SERVING, self._check("iplms.ai.copilot.v1.CopilotService"))
        self.assertEqual(
            self.status.SERVING,
            self._check("iplms.ai.copilot.v1.CopilotService", base_url="http://localhost:11434/v1"),
        )

    def test_knowledge_needs_embedding(self):
        service = "iplms.ai.knowledge.v1.KnowledgeService"
        self.assertEqual(self.status.NOT_SERVING, self._check(service, base_url="http://ollama/v1"))
        self.assertEqual(self.status.SERVING, self._check(service, key="sk-test"))

    def test_vision_does_not_depend_on_llm(self):
        self.assertEqual(self.status.SERVING, self._check("iplms.ai.vision.v1.VisionService"))

    def test_unknown_service(self):
        self.assertEqual(self.status.SERVICE_UNKNOWN, self._check("nope.Service"))


if __name__ == "__main__":
    unittest.main()
