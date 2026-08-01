"""统一响应结构 ApiResponse = {code, message, data}（对齐前端契约）。"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None


def ok(data: T | None = None, message: str = "success") -> ApiResponse[T]:
    return ApiResponse(code=200, message=message, data=data)


def fail(message: str, code: int = 400) -> ApiResponse:
    return ApiResponse(code=code, message=message, data=None)
