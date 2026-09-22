import uuid

from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Usuario de la petición en curso, entregado por get_current_user."""

    id: uuid.UUID
    supertokens_user_id: str


class MeRead(BaseModel):
    id: uuid.UUID
    email: str | None
