"""Interceptor chạy trước mọi handler — thêm interceptor mới thì khai báo ở đây."""
from typing import List

from grpc import aio

from app.api.grpc.interceptors.logging_interceptor import LoggingInterceptor


def build_interceptors() -> List[aio.ServerInterceptor]:
    return [LoggingInterceptor()]


__all__ = ["LoggingInterceptor", "build_interceptors"]
