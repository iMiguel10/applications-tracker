import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    # Los límites coinciden con las columnas: un texto demasiado largo es un 422
    # explicado, no un error de Postgres convertido en 500.
    model_config = ConfigDict(str_strip_whitespace=True)

    position_title: str = Field(min_length=1, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position_title: str
    company_name: str
    created_at: datetime
