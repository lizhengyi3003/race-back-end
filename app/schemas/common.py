"""通用分页结构"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageData(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    items: list[T]
