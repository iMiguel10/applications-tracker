from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.domain.application import MAX_NOTES_LENGTH


def _empty_to_none(value: Any) -> Any:
    """Un formulario envía "" al vaciar un campo: se guarda como NULL, no como texto vacío."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


RequiredName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
OptionalShortText = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None,
    BeforeValidator(_empty_to_none),
]
OptionalMediumText = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None,
    BeforeValidator(_empty_to_none),
]
OptionalNotes = Annotated[
    Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=MAX_NOTES_LENGTH)
    ]
    | None,
    BeforeValidator(_empty_to_none),
]
OptionalUrl = Annotated[
    Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, max_length=2000, pattern=r"^https?://\S+$"
        ),
    ]
    | None,
    BeforeValidator(_empty_to_none),
]

SortOrder = Literal["asc", "desc"]


class ErrorResponse(BaseModel):
    """Error de negocio. `code` es estable (contrato); `detail` es informativo."""

    detail: str = Field(examples=["Company not found"])
    code: str = Field(examples=["not_found"])


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Respuestas de error documentadas en el OpenAPI de un endpoint."""
    descriptions = {
        404: "No existe o pertenece a otro usuario (no se distingue).",
        409: "Una regla de negocio impide la operación; ver `code`.",
        422: "Datos no válidos.",
    }
    return {
        code: {"model": ErrorResponse, "description": descriptions[code]}
        for code in codes
    }
