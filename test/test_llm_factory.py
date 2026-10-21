import asyncio
import unittest
from types import SimpleNamespace

from app.infra.llm.llm_factory import LlmFactory


class FakeResponses:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            async def events():
                yield SimpleNamespace(type="response.created")
                yield SimpleNamespace(type="response.output_text.delta", delta="Xin ")
                yield SimpleNamespace(type="response.output_text.delta", delta="chào")
                yield SimpleNamespace(type="response.completed")
            return events()
        return SimpleNamespace(output_text="Câu trả lời có nguồn")


class LlmFactoryTest(unittest.TestCase):
    def setUp(self):
        self.responses = FakeResponses()
        self.factory = LlmFactory(client=SimpleNamespace(responses=self.responses))

    def test_unary_uses_responses_api_without_provider_storage(self):
        answer = asyncio.run(self.factory.generate_response("system", "question", "context"))
        self.assertEqual("Câu trả lời có nguồn", answer)
        self.assertFalse(self.responses.calls[0]["store"])
        self.assertIn("NGỮ CẢNH", self.responses.calls[0]["input"])

    def test_stream_yields_only_text_delta_events(self):
        async def collect():
            return [token async for token in self.factory.stream_response("s", "q", "c")]

        self.assertEqual(["Xin ", "chào"], asyncio.run(collect()))
        self.assertTrue(self.responses.calls[0]["stream"])


class FakeChat:
    def __init__(self, content):
        self.calls = []
        self._content = content
        self.completions = self

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class LlmProviderTest(unittest.TestCase):
    """ISSUE-011: OpenAI hoặc endpoint tương thích (Ollama) chỉ bằng cấu hình."""

    def _factory(self, base_url="", api_key="", client=None):
        factory = LlmFactory(api_key=api_key, client=client)
        factory.api_key = api_key
        factory.base_url = base_url
        return factory

    def test_missing_key_without_base_url_is_precondition_error(self):
        from app.core.exceptions import ModelNotLoadedError

        with self.assertRaises(ModelNotLoadedError):
            self._factory()._get_client()

    def test_base_url_without_key_uses_placeholder_key(self):
        client = self._factory(base_url="http://localhost:11434/v1")._get_client()
        self.assertEqual("http://localhost:11434/v1", str(client.base_url).rstrip("/"))
        self.assertEqual("ollama", client.api_key)

    def test_openai_json_uses_responses_structured_outputs(self):
        responses = FakeResponses()

        async def create(**kwargs):
            responses.calls.append(kwargs)
            return SimpleNamespace(output_text='{"ok": true}')

        responses.create = create
        factory = self._factory(api_key="sk-test", client=SimpleNamespace(responses=responses))
        payload = asyncio.run(factory.generate_json("i", "x", "s", {"type": "object"}))
        self.assertEqual({"ok": True}, payload)
        self.assertEqual("json_schema", responses.calls[0]["text"]["format"]["type"])

    def test_compatible_endpoint_json_uses_chat_response_format(self):
        chat = FakeChat('{"cases": []}')
        factory = self._factory(
            base_url="http://localhost:11434/v1", client=SimpleNamespace(chat=chat)
        )
        payload = asyncio.run(factory.generate_json("i", "x", "cases", {"type": "object"}))
        self.assertEqual({"cases": []}, payload)
        call = chat.calls[0]
        self.assertEqual("json_schema", call["response_format"]["type"])
        self.assertEqual("cases", call["response_format"]["json_schema"]["name"])
        self.assertEqual("system", call["messages"][0]["role"])

    def test_compatible_endpoint_bad_json_is_an_error_not_swallowed(self):
        from app.core.exceptions import RagPipelineError

        factory = self._factory(
            base_url="http://localhost:11434/v1",
            client=SimpleNamespace(chat=FakeChat("không phải json")),
        )
        with self.assertRaises(RagPipelineError):
            asyncio.run(factory.generate_json("i", "x", "s", {"type": "object"}))

    def test_model_not_found_raises_model_configuration_error_with_model_name(self):
        import httpx
        from openai import NotFoundError
        from app.core.exceptions import ModelConfigurationError

        req = httpx.Request("POST", "http://localhost:11434/v1/chat/completions")
        res = httpx.Response(404, request=req)
        err = NotFoundError("model 'khong-ton-tai:1b' not found", response=res, body=None)

        class FailingChat:
            completions = None
            def __init__(self):
                self.completions = self
            async def create(self, **kwargs):
                raise err

        factory = self._factory(
            base_url="http://localhost:11434/v1",
            client=SimpleNamespace(chat=FailingChat()),
        )
        factory.model = "khong-ton-tai:1b"

        with self.assertRaises(ModelConfigurationError) as ctx:
            asyncio.run(factory.generate_json("i", "x", "s", {"type": "object"}))

        self.assertIn("khong-ton-tai:1b", str(ctx.exception))
        self.assertIn("Provider không có model", str(ctx.exception))

    def test_connection_error_raises_model_configuration_error_with_provider_url(self):
        import httpx
        from openai import APIConnectionError
        from app.core.exceptions import ModelConfigurationError

        req = httpx.Request("POST", "http://localhost:11434/v1/chat/completions")
        err = APIConnectionError(request=req)

        class FailingChat:
            completions = None
            def __init__(self):
                self.completions = self
            async def create(self, **kwargs):
                raise err

        factory = self._factory(
            base_url="http://localhost:11434/v1",
            client=SimpleNamespace(chat=FailingChat()),
        )

        with self.assertRaises(ModelConfigurationError) as ctx:
            asyncio.run(factory.generate_json("i", "x", "s", {"type": "object"}))

        self.assertIn("http://localhost:11434/v1", str(ctx.exception))
        self.assertIn("Không kết nối được provider", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

