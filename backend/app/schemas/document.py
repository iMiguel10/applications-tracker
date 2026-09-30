import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.documents import DocumentKind, DocumentOrigin, DocumentStatus
from app.schemas.common import RequiredName


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: DocumentKind = Field(description="`cv` o `cover_letter`.")
    origin: DocumentOrigin = Field(
        description="De dónde sale (RF-91): `uploaded` (subido), `generated` "
        "(desde el perfil) o `ai_tailored` (adaptado con IA)."
    )
    status: DocumentStatus = Field(
        description="`ready` si el PDF se puede descargar. Uno subido nace `ready`; "
        "uno generado pasa por `pending` y puede acabar en `failed`."
    )
    name: str = Field(
        description="Nombre visible. El del fichero subido, saneado: solo se "
        "muestra, nunca se usa como ruta.",
        examples=["CV backend 2026.pdf"],
    )
    size_bytes: int | None = Field(
        description="Tamaño en bytes. `null` mientras no hay fichero."
    )
    archived_at: datetime | None = Field(
        description="Si está archivado (RF-93): fuera de la biblioteca, pero sigue "
        "asociado a sus solicitudes y ocupando almacenamiento."
    )
    created_at: datetime
    updated_at: datetime


class DocumentListItemRead(DocumentRead):
    applications_count: int = Field(
        description="En cuántas solicitudes se envió como CV o como carta (RF-92). "
        "Cuáles, en `GET /documents/{document_id}`. Mayor que 0: no se puede borrar."
    )


class DocumentListQuery(BaseModel):
    """Filtros de la biblioteca (RF-90)."""

    page: int = Field(default=1, ge=1, description="Página, empezando en 1.")
    limit: int = Field(default=20, ge=1, le=100, description="Elementos por página.")
    kind: DocumentKind | None = Field(default=None, description="Solo este tipo.")
    archived: bool = Field(
        default=False,
        description="`false` (por defecto): la biblioteca. `true`: solo los "
        "archivados.",
    )


class DocumentUpdate(BaseModel):
    """RF-90: renombrar. El tipo no cambia: un documento ya asociado a una solicitud
    como CV dejaría de serlo."""

    name: RequiredName = Field(
        description="Nombre visible nuevo. Se sanea igual que al subir.",
        examples=["CV backend 2026.pdf"],
    )


class DocumentSummary(BaseModel):
    """Un documento dentro de otro recurso (el CV y la carta de una solicitud)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: DocumentKind
    name: str
    status: DocumentStatus
    archived_at: datetime | None = Field(
        description="Archivado: fuera de la biblioteca, pero sigue asociado."
    )


class DocumentUsageRead(BaseModel):
    """Una solicitud en la que se envió el documento (RF-92)."""

    model_config = ConfigDict(from_attributes=True)

    application_id: uuid.UUID
    position_title: str
    company_name: str
    used_as: DocumentKind = Field(description="Cómo se envió: `cv` o `cover_letter`.")
    application_archived: bool


class DocumentDetailRead(DocumentRead):
    used_in: list[DocumentUsageRead] = Field(
        description="Solicitudes en las que se envió, archivadas incluidas (RF-92). "
        "Mientras haya alguna, el documento no se puede borrar (RF-93)."
    )
