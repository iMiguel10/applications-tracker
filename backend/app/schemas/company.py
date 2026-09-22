import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import (
    OptionalNotes,
    OptionalShortText,
    OptionalUrl,
    RequiredName,
    SortOrder,
)


class CompanyCreate(BaseModel):
    name: RequiredName = Field(
        description="Nombre. Único por usuario sin distinguir mayúsculas.",
        examples=["Acme"],
    )
    website: OptionalUrl = Field(default=None, examples=["https://acme.example"])
    location: OptionalShortText = Field(default=None, examples=["Madrid"])
    notes: OptionalNotes = Field(default=None, description="Máximo 5 000 caracteres.")


class CompanyUpdate(BaseModel):
    """Actualización parcial: solo se modifican los campos enviados. Enviar `null`
    vacía un campo opcional."""

    name: RequiredName | None = Field(default=None, examples=["Acme Corp"])
    website: OptionalUrl = None
    location: OptionalShortText = None
    notes: OptionalNotes = None


class CompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str = Field(examples=["Acme"])


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str = Field(examples=["Acme"])
    website: str | None
    location: str | None
    notes: str | None
    applications_count: int = Field(
        description="Solicitudes a esta empresa, incluidas las archivadas."
    )
    created_at: datetime
    updated_at: datetime


class CompanyListQuery(BaseModel):
    page: int = Field(default=1, ge=1, description="Página, empezando en 1.")
    limit: int = Field(default=20, ge=1, le=100, description="Elementos por página.")
    q: str | None = Field(
        default=None, max_length=200, description="Busca en el nombre (contiene)."
    )
    sort_by: Literal["name", "created_at", "applications_count"] = "name"
    order: SortOrder = "asc"
