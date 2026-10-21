"""Interceptor log mọi RPC + quy exception về đúng gRPC status.

Handler không cần try/except: lỗi nghiệp vụ ném thẳng, tới đây mới quy về status.
Bảng ánh xạ dưới đây PHẢI phủ hết `core.exceptions` — sai một dòng là NestJS
nhận 500 cho lỗi vốn của người dùng (ảnh mờ, không có biển).
"""
import time

import grpc
from grpc import aio

from app.core.exceptions import (
    AiServiceError,
    ConsoleStoreError,
    FeatureNotImplementedError,
    FraudDetectedError,
    InvalidImageError,
    KnowledgeGateError,
    ModelConfigurationError,
    ModelNotLoadedError,
    PlateRecognitionError,
    RagPipelineError,
)
from app.util.logger import logger

# Thứ tự có ý nghĩa: lớp con đứng trước lớp cha.
_STATUS_BY_EXCEPTION: tuple[tuple[type[Exception], grpc.StatusCode], ...] = (
    # Lỗi do dữ liệu client gửi lên → client sửa được, KHÔNG phải sự cố hệ thống.
    (InvalidImageError, grpc.StatusCode.INVALID_ARGUMENT),
    (ValueError, grpc.StatusCode.INVALID_ARGUMENT),
    # Ảnh hợp lệ nhưng không tìm ra biển → "không có kết quả", không phải lỗi.
    (PlateRecognitionError, grpc.StatusCode.NOT_FOUND),
    # Kết luận nghiệp vụ, không phải hỏng hóc.
    (FraudDetectedError, grpc.StatusCode.FAILED_PRECONDITION),
    # Thiếu checkpoint/model → server chưa sẵn sàng, client retry sau có thể được.
    (ModelNotLoadedError, grpc.StatusCode.FAILED_PRECONDITION),
    # Cổng nghiệp vụ Knowledge Base (bộ test trống, chưa đạt ngưỡng…) → message
    # đi thẳng tới người dùng qua backend.
    (KnowledgeGateError, grpc.StatusCode.FAILED_PRECONDITION),
    # Lỗi cấu hình model/provider (không có model, không kết nối được provider)
    (ModelConfigurationError, grpc.StatusCode.FAILED_PRECONDITION),
    # Hạ tầng phía sau (pgvector, LLM) hỏng.
    (RagPipelineError, grpc.StatusCode.UNAVAILABLE),
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


class LoggingInterceptor(aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        method = handler_call_details.method

        if handler.unary_unary is not None:
            inner = handler.unary_unary

            async def unary(request, context):
                started = time.perf_counter()
                try:
                    response = await inner(request, context)
                except Exception as exc:
                    await _abort(context, method, exc)
                    raise
                logger.info(f"{method} OK in {(time.perf_counter() - started) * 1000:.1f}ms")
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
