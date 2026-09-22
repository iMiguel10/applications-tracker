import math
from typing import Self

from pydantic import BaseModel


class Page[T](BaseModel):
    """Respuesta paginada común a todos los listados: {items, total, page, limit, pages}."""

    items: list[T]
    total: int
    page: int
    limit: int
    pages: int

    @classmethod
    def build(cls, items: list[T], *, total: int, page: int, limit: int) -> Self:
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if total else 0,
        )
