"""Envelope REST dùng chung cho mọi route FastAPI của AI service.

Khác envelope `ApiResponse` bên NestJS — đây là hợp đồng nội bộ giữa `ai/` và
`AnprProvider` (infrastructures/Anpr) nên giữ nguyên tên field.
"""
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    success: bool
    total: int
    message: str
    data: List[T]

    @classmethod
    def ok(cls, data: List[T], message: str) -> "BaseResponse[T]":
        return cls(success=True, total=len(data), message=message, data=data)

    @classmethod
    def fail(cls, message: str) -> "BaseResponse[T]":
        return cls(success=False, total=0, message=message, data=[])
