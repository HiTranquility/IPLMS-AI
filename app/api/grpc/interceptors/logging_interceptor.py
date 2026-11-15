"""Interceptor log mọi RPC + quy exception về đúng gRPC status.

Handler không cần try/except: lỗi nghiệp vụ ném thẳng, tới đây mới quy về status.
Bảng ánh xạ dưới đây PHẢI phủ hết `core.exceptions` — sai một dòng là NestJS
nhận 500 cho lỗi vốn của người dùng (ảnh mờ, không có biển).
"""
import hmac
import re
import time

import grpc
from grpc import aio

from app.config import get_config

from app.core.exceptions import (
    AiServiceError,
    ConsoleAccessDenied,
    ConsoleAuthError,
    ConsoleRateLimited,
    ConsoleStoreError,
    DataLakeError,
    DocumentTooLargeError,
    EmbeddingError,
    FeatureNotImplementedError,
    FraudDetectedError,
    InvalidImageError,
    KnowledgeGateError,
    ModelConfigurationError,
    ModelNotLoadedError,
    NoTextLayerError,
    PlateRecognitionError,
    RagPipelineError,
    UnsupportedFormatError,
    WorkflowConfigurationError,
    WorkflowStateError,
)
from app.util.logger import logger

# Thứ tự có ý nghĩa: lớp con đứng trước lớp cha.
_STATUS_BY_EXCEPTION: tuple[tuple[type[Exception], grpc.StatusCode], ...] = (
    # Lỗi do dữ liệu client gửi lên → client sửa được, KHÔNG phải sự cố hệ thống.
    (InvalidImageError, grpc.StatusCode.INVALID_ARGUMENT),
    (UnsupportedFormatError, grpc.StatusCode.INVALID_ARGUMENT),
    (NoTextLayerError, grpc.StatusCode.INVALID_ARGUMENT),
    (DocumentTooLargeError, grpc.StatusCode.INVALID_ARGUMENT),
    (WorkflowStateError, grpc.StatusCode.INVALID_ARGUMENT),
    (ValueError, grpc.StatusCode.INVALID_ARGUMENT),
    # Ảnh hợp lệ nhưng không tìm ra biển → "không có kết quả", không phải lỗi.
    (PlateRecognitionError, grpc.StatusCode.NOT_FOUND),
    # Xác thực / phân quyền / giới hạn tốc độ AI Console.
    (ConsoleAuthError, grpc.StatusCode.UNAUTHENTICATED),
    (ConsoleAccessDenied, grpc.StatusCode.PERMISSION_DENIED),
    (ConsoleRateLimited, grpc.StatusCode.RESOURCE_EXHAUSTED),
    # Kết luận nghiệp vụ, không phải hỏng hóc.
    (FraudDetectedError, grpc.StatusCode.FAILED_PRECONDITION),
    # Thiếu checkpoint/model → server chưa sẵn sàng, client retry sau có thể được.
    (ModelNotLoadedError, grpc.StatusCode.FAILED_PRECONDITION),
    # Cổng nghiệp vụ Knowledge Base (bộ test trống, chưa đạt ngưỡng…) → message
    # đi thẳng tới người dùng qua backend.
    (KnowledgeGateError, grpc.StatusCode.FAILED_PRECONDITION),
    # Lỗi cấu hình model/provider hoặc workflow (không có model, thiếu cấu hình).
    (ModelConfigurationError, grpc.StatusCode.FAILED_PRECONDITION),
    (WorkflowConfigurationError, grpc.StatusCode.FAILED_PRECONDITION),
    # Hạ tầng phía sau (pgvector, LLM, data lake) hỏng.
    (EmbeddingError, grpc.StatusCode.UNAVAILABLE),
    (RagPipelineError, grpc.StatusCode.UNAVAILABLE),
    (DataLakeError, grpc.StatusCode.UNAVAILABLE),
    # DB AI Console (kênh A2) không truy cập được → backend thử lại ở chu kỳ sau.
    (ConsoleStoreError, grpc.StatusCode.UNAVAILABLE),
    # Khai trong proto nhưng nghiệp vụ chưa có thật. UNIMPLEMENTED chứ không phải
    # INTERNAL: đây không phải sự cố, và client KHÔNG nên retry.
    (FeatureNotImplementedError, grpc.StatusCode.UNIMPLEMENTED),
    # Bắt sót AiServiceError nào chưa liệt kê ở trên.
    (AiServiceError, grpc.StatusCode.INTERNAL),
)


def status_for(exc: Exception) -> grpc.StatusCode:
    for exc_type, code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return code
    return grpc.StatusCode.INTERNAL


_HEALTH_CHECK_METHOD = "/grpc.health.v1.Health/Check"
_INTERNAL_TOKEN_METADATA_KEY = "x-internal-token"
_CORRELATION_METADATA_KEYS = ("x-request-id", "x-correlation-id")
_SAFE_CORRELATION_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _extract_correlation_id(handler_call_details) -> str:
    metadata = getattr(handler_call_details, "invocation_metadata", None) or ()
    for item in metadata:
        key = getattr(item, "key", item[0] if isinstance(item, tuple) else "")
        value = getattr(item, "value", item[1] if isinstance(item, tuple) else "")
        if key in _CORRELATION_METADATA_KEYS and isinstance(value, str):
            candidate = value.strip()
            if _SAFE_CORRELATION_ID_RE.match(candidate):
                return candidate
    return "-"


def _has_valid_internal_token(handler_call_details, expected_token: str) -> bool:
    active_keys = [k.strip() for k in (expected_token or "").split(",") if k.strip()]
    if not active_keys:
        return True
    if getattr(handler_call_details, "method", None) == _HEALTH_CHECK_METHOD:
        return True
    metadata = getattr(handler_call_details, "invocation_metadata", None) or ()
    for item in metadata:
        key = getattr(item, "key", item[0] if isinstance(item, tuple) else "")
        value = getattr(item, "value", item[1] if isinstance(item, tuple) else "")
        if key == _INTERNAL_TOKEN_METADATA_KEY and isinstance(value, str):
            candidate = value.strip()
            matched = False
            for secret in active_keys:
                if hmac.compare_digest(candidate, secret):
                    matched = True
            return matched
    return False


class LoggingInterceptor(aio.ServerInterceptor):
    def __init__(self, expected_token: str | None = None) -> None:
        self._expected_token = expected_token

    def _resolve_expected_token(self) -> str:
        if self._expected_token is not None:
            return self._expected_token
        return get_config().server.internal_api_token

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        method = handler_call_details.method
        correlation_id = _extract_correlation_id(handler_call_details)
        expected_token = self._resolve_expected_token()
        if not _has_valid_internal_token(handler_call_details, expected_token):
            async def _unauthenticated_unary(request, context):
                logger.warning(f"{method} → UNAUTHENTICATED: Missing or invalid x-internal-token")
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED,
                    "Missing or invalid x-internal-token",
                )

            async def _unauthenticated_stream(request, context):
                logger.warning(f"{method} → UNAUTHENTICATED: Missing or invalid x-internal-token")
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED,
                    "Missing or invalid x-internal-token",
                )
                if False:  # pragma: no cover - keeps generator signature for unary_stream
                    yield None

            if handler.unary_stream is not None:
                return grpc.unary_stream_rpc_method_handler(
                    _unauthenticated_stream,
                    request_deserializer=handler.request_deserializer,
                    response_serializer=handler.response_serializer,
                )
            return grpc.unary_unary_rpc_method_handler(
                _unauthenticated_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_unary is not None:
            inner = handler.unary_unary

            async def unary(request, context):
                started = time.perf_counter()
                try:
                    response = await inner(request, context)
                except Exception as exc:
                    await _abort(context, method, exc)
                    raise
                logger.info(f"{method} OK in {(time.perf_counter() - started) * 1000:.1f}ms rid={correlation_id}")
                return response

            return grpc.unary_unary_rpc_method_handler(
                unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream is not None:
            inner = handler.unary_stream

            async def unary_stream(request, context):
                started = time.perf_counter()
                try:
                    async for message in inner(request, context):
                        yield message
                except Exception as exc:
                    await _abort(context, method, exc)
                    raise
                logger.info(f"{method} stream done in {(time.perf_counter() - started) * 1000:.1f}ms")

            return grpc.unary_stream_rpc_method_handler(
                unary_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler


async def _abort(context, method: str, exc: Exception) -> None:
    code = status_for(exc)
    # Lỗi do input của client thì log mức warning — đừng làm nhiễu cảnh báo prod.
    if code in (grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.NOT_FOUND):
        logger.warning(f"{method} → {code.name}: {exc}")
    else:
        logger.exception(f"{method} → {code.name}: {exc}")
    await context.abort(code, str(exc))
