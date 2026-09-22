import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    # Los límites coinciden con las columnas: un texto demasiado largo es un 422
    # explicado, no un error de Postgres convertido en 500.
    model_config = ConfigDict(str_strip_whitespace=True)

    position_title: str = Field(
        min_length=1,
        max_length=200,
        description="Puesto al que se aplica. Se recortan los espacios de los extremos.",
        examples=["Backend Developer"],
    )
    company_name: str = Field(
        min_length=1,
        max_length=200,
        description="Empresa. En F2 pasará a ser una referencia a una empresa registrada.",
        examples=["Acme"],
    )


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Identificador de la solicitud.")
    position_title: str = Field(examples=["Backend Developer"])
    company_name: str = Field(examples=["Acme"])
    created_at: datetime = Field(description="Momento de creación, en UTC.")
