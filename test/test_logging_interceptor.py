import unittest

try:
    import grpc
    from app.api.grpc.interceptors.logging_interceptor import (
        _STATUS_BY_EXCEPTION,
        status_for,
    )
except ImportError:
    grpc = None  # type: ignore[assignment]
    _STATUS_BY_EXCEPTION = ()  # type: ignore[assignment]
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


if __name__ == "__main__":
    unittest.main()
