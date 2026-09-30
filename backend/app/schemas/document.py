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
