import math
from typing import Self

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    """Respuesta paginada común a todos los listados: {items, total, page, limit, pages}."""

    items: list[T] = Field(description="Elementos de la página pedida.")
    total: int = Field(description="Total de elementos que cumplen el filtro.")
    page: int = Field(description="Página devuelta, empezando en 1.")
    limit: int = Field(description="Tamaño de página pedido.")
    pages: int = Field(description="Número total de páginas (0 si no hay elementos).")

    @classmethod
    def build(cls, items: list[T], *, total: int, page: int, limit: int) -> Self:
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if total else 0,
        )
