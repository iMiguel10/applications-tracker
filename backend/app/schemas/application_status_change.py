import uuid
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.application_status import ApplicationStatus
from app.schemas.common import OptionalNotes


class ApplicationStatusChangeCreate(BaseModel):
    """Cuerpo de `POST /applications/{id}/status-changes` (RF-30)."""

    to_status: ApplicationStatus = Field(
        description="Debe estar entre las `allowed_transitions` de la solicitud."
    )
    # AwareDatetime: exige zona horaria. Una hora "naive" sería ambigua (¿UTC? ¿la
    # del navegador?), y la arquitectura fija timestamptz en UTC para todo instante.
    changed_at: AwareDatetime | None = Field(
        default=None,
        description="Cuándo ocurrió de verdad. Por defecto, ahora. Puede ser una "
        "fecha pasada, pero nunca anterior al último cambio ni posterior a ahora.",
    )
    note: OptionalNotes = Field(default=None, description="Máximo 5 000 caracteres.")


class ApplicationStatusChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: ApplicationStatus | None = Field(
        description="`null` en el cambio inicial, que crea la solicitud."
    )
    to_status: ApplicationStatus
    changed_at: datetime
    note: str | None
    created_at: datetime = Field(
        description="Cuándo se registró en el sistema. Informativo: el orden real "
        "del historial no se expone (es `seq`, una columna interna)."
    )
