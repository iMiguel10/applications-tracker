import uuid

from pydantic import BaseModel, Field


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
