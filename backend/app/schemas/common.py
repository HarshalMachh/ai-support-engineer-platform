from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

ItemT = TypeVar("ItemT")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list[ItemT], total: int, page: int, page_size: int) -> "Page[ItemT]":
        return cls(items=items, total=total, page=page, page_size=page_size, pages=max(1, ceil(total / page_size)))


class MessageResponse(BaseModel):
    message: str
