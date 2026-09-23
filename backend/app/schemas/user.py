import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.domain.user import MAX_STALE_AFTER_DAYS, MIN_STALE_AFTER_DAYS, Language


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


class PreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: Language | None = Field(
        description="`null`: sigue el idioma del navegador."
    )
    stale_after_days: StaleAfterDays = Field(
        description="RF-64: días sin actividad para avisar en el dashboard."
    )


class PreferencesUpdate(BaseModel):
    language: Language | None = None
    stale_after_days: StaleAfterDays | None = None
