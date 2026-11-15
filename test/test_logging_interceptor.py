from types import SimpleNamespace
import unittest

try:
    import grpc
    from app.api.grpc.interceptors.logging_interceptor import (
        _STATUS_BY_EXCEPTION,
        _extract_correlation_id,
        _has_valid_internal_token,
        status_for,
    )
except ImportError:
    grpc = None  # type: ignore[assignment]
    _STATUS_BY_EXCEPTION = ()  # type: ignore[assignment]
    _extract_correlation_id = None  # type: ignore[assignment]
    _has_valid_internal_token = None  # type: ignore[assignment]
    status_for = None  # type: ignore[assignment]

from app.core.exceptions import AiServiceError, EmbeddingError, ModelConfigurationError


@unittest.skipIf(grpc is None, "grpcio chưa cài trong môi trường này")
class TestLoggingInterceptor(unittest.TestCase):
    def test_all_ai_service_error_subclasses_explicitly_mapped(self) -> None:
        mapped_types = {exc_type for exc_type, _ in _STATUS_BY_EXCEPTION}
        subclasses = set(AiServiceError.__subclasses__())
        missing = subclasses - mapped_types
        self.assertEqual(
            missing,
            set(),
            f"Các lớp con AiServiceError chưa khai trong _STATUS_BY_EXCEPTION: {missing}",
        )

    def test_status_for_specific_exceptions(self) -> None:
        assert status_for is not None
        assert grpc is not None
        self.assertEqual(status_for(EmbeddingError("ollama down")), grpc.StatusCode.UNAVAILABLE)
        self.assertEqual(
            status_for(ModelConfigurationError("missing model")),
            grpc.StatusCode.FAILED_PRECONDITION,
        )

    def test_internal_token_verification_allows_when_unconfigured_or_health_check(self) -> None:
        assert _has_valid_internal_token is not None
        call_no_meta = SimpleNamespace(
            method="/iplms.ai.v1.VisionService/RecognizePlate",
            invocation_metadata=(),
        )
        self.assertTrue(_has_valid_internal_token(call_no_meta, ""))
        self.assertFalse(_has_valid_internal_token(call_no_meta, "secret-token-2026"))

        health_call = SimpleNamespace(
            method="/grpc.health.v1.Health/Check",
            invocation_metadata=(),
        )
        self.assertTrue(_has_valid_internal_token(health_call, "secret-token-2026"))

    def test_internal_token_verification_checks_metadata_constant_time(self) -> None:
        assert _has_valid_internal_token is not None
        valid_call = SimpleNamespace(
            method="/iplms.ai.v1.VisionService/RecognizePlate",
            invocation_metadata=(("x-internal-token", "secret-token-2026"),),
        )
        invalid_call = SimpleNamespace(
            method="/iplms.ai.v1.VisionService/RecognizePlate",
            invocation_metadata=(("x-internal-token", "wrong-token"),),
        )
        self.assertTrue(_has_valid_internal_token(valid_call, "secret-token-2026"))
        self.assertFalse(_has_valid_internal_token(invalid_call, "secret-token-2026"))
        # Zero-Downtime Key-Ring Rotation: accept both primary (new) and secondary (retiring) keys
        self.assertTrue(
            _has_valid_internal_token(valid_call, "new-token-2027, secret-token-2026")
        )
        new_call = SimpleNamespace(
            method="/iplms.ai.v1.VisionService/RecognizePlate",
            invocation_metadata=(("x-internal-token", "new-token-2027"),),
        )
        self.assertTrue(
            _has_valid_internal_token(new_call, "new-token-2027, secret-token-2026")
        )
        self.assertFalse(
            _has_valid_internal_token(invalid_call, "new-token-2027, secret-token-2026")
        )

    def test_extract_correlation_id_sanitizes_crlf_injection(self) -> None:
        assert _extract_correlation_id is not None
        ok_call = SimpleNamespace(
            method="/iplms.ai.v1.VisionService/RecognizePlate",
            invocation_metadata=(("x-correlation-id", "req-2026_abc.1"),),
        )
        bad_call = SimpleNamespace(
            method="/iplms.ai.v1.VisionService/RecognizePlate",
            invocation_metadata=(("x-request-id", "bad\r\nFAKE LOG LINE"),),
        )
        self.assertEqual(_extract_correlation_id(ok_call), "req-2026_abc.1")
        self.assertEqual(_extract_correlation_id(bad_call), "-")


if __name__ == "__main__":
    unittest.main()
