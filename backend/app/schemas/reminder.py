import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.domain.reminder import ReminderChannel, ReminderStatus
from app.schemas.common import RequiredName, SortOrder


class ReminderCreate(BaseModel):
    title: RequiredName = Field(examples=["Enviar el test técnico"])
    due_at: AwareDatetime = Field(description="Fecha límite.")
    application_id: uuid.UUID | None = Field(
        default=None, description="Solicitud asociada (opcional, RF-50)."
    )


class ReminderApplicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position_title: str = Field(examples=["Backend Developer"])


class ReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str = Field(examples=["Enviar el test técnico"])
    due_at: datetime
    application: ReminderApplicationSummary | None
    sent_at: datetime | None = Field(
        description="`null` en el MVP: el único canal (in_app) no envía nada (RF-53)."
    )
    completed_at: datetime | None
    channel: ReminderChannel
    status: ReminderStatus
    created_at: datetime
    updated_at: datetime


ReminderStatusFilter = Literal["pending", "done", "dismissed", "all"]
ReminderSortField = Literal["due_at", "created_at"]

_STATUS_FILTER: dict[str, list[str]] = {
    "pending": [ReminderStatus.PENDING.value],
    "done": [ReminderStatus.DONE.value],
    "dismissed": [ReminderStatus.DISMISSED.value],
    "all": [],
}


class ReminderListQuery(BaseModel):
    """Filtros del listado (RF-52)."""

    page: int = Field(default=1, ge=1, description="Página, empezando en 1.")
    limit: int = Field(default=20, ge=1, le=100, description="Elementos por página.")
    application_id: uuid.UUID | None = Field(
        default=None, description="Solo los recordatorios de esta solicitud."
    )
    status: ReminderStatusFilter = Field(
        default="pending",
        description="`pending` (por defecto), `done`, `dismissed` o `all`.",
    )
    due_before: AwareDatetime | None = None
    due_after: AwareDatetime | None = None
    sort_by: ReminderSortField = "due_at"
    order: SortOrder = "asc"

    @property
    def statuses(self) -> list[str]:
        return _STATUS_FILTER[self.status]

    @model_validator(mode="after")
    def _due_range(self) -> Self:
        if self.due_after and self.due_before and self.due_after > self.due_before:
            raise ValueError("due_after cannot be after due_before")
        return self
