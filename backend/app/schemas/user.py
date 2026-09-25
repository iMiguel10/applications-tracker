import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.domain.user import (
    MAX_STALE_AFTER_DAYS,
    MAX_TIMEZONE_LENGTH,
    MIN_STALE_AFTER_DAYS,
    Language,
    is_valid_timezone,
)


class CurrentUser(BaseModel):
    """Usuario de la petición en curso, entregado por get_current_user."""

    id: uuid.UUID
    supertokens_user_id: str


class MeRead(BaseModel):
    id: uuid.UUID = Field(description="Identificador del usuario en esta API.")
    email: str | None = Field(
        description="Email de la cuenta, leído de SuperTokens en cada petición.",
        examples=["ana@example.com"],
    )


StaleAfterDays = Annotated[int, Field(ge=MIN_STALE_AFTER_DAYS, le=MAX_STALE_AFTER_DAYS)]


def _known_timezone(value: str) -> str:
    if not is_valid_timezone(value):
        raise ValueError("Unknown time zone: use an IANA name such as Europe/Madrid")
    return value


Timezone = Annotated[
    str,
    Field(max_length=MAX_TIMEZONE_LENGTH, examples=["Europe/Madrid"]),
    AfterValidator(_known_timezone),
]


class PreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: Language | None = Field(
        description="`null`: sigue el idioma del navegador."
    )
    stale_after_days: StaleAfterDays = Field(
        description="RF-64: días sin actividad para avisar en el dashboard."
    )
    timezone: str | None = Field(
        description="RF-07: zona horaria IANA (`Europe/Madrid`). `null` hasta que "
        "el cliente la fija; mientras tanto se usa UTC.",
        examples=["Europe/Madrid"],
    )


class PreferencesUpdate(BaseModel):
    language: Language | None = None
    stale_after_days: StaleAfterDays | None = None
    timezone: Timezone | None = Field(
        default=None,
        description="Nombre IANA de una zona conocida; otro valor responde 422. "
        "La aplicación web envía la del navegador si la cuenta aún no tiene.",
    )
