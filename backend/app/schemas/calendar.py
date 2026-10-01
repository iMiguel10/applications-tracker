import uuid
from datetime import datetime
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.domain.calendar import MAX_CALENDAR_RANGE, CalendarEventKind
from app.domain.interview import InterviewFormat, InterviewOutcome, InterviewType
from app.schemas.company import CompanySummary


class CalendarEventsQuery(BaseModel):
    """El rango que pinta la vista (RF-130): un mes o una semana."""

    start: AwareDatetime = Field(description="Inicio del rango, incluido.")
    end: AwareDatetime = Field(
        description="Fin del rango, excluido. Como mucho 62 días después de `start`."
    )

    @model_validator(mode="after")
    def _range(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        if self.end - self.start > MAX_CALENDAR_RANGE:
            raise ValueError("the range cannot be longer than 62 days")
        return self


class CalendarApplication(BaseModel):
    """La solicitud de un evento, lo justo para nombrarlo y enlazarla (RF-131)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position_title: str = Field(examples=["Backend Developer"])
    company: CompanySummary


class CalendarEvent(BaseModel):
    """Una entrevista o un recordatorio pendiente. Los campos de entrevista son
    `null` en un recordatorio, y `title` es `null` en una entrevista."""

    kind: CalendarEventKind
    id: uuid.UUID
    starts_at: datetime = Field(
        description="Hora de la entrevista o vencimiento del recordatorio."
    )
    duration_minutes: int | None = None
    title: str | None = Field(default=None, examples=["Enviar el test técnico"])
    interview_type: InterviewType | None = None
    format: InterviewFormat | None = None
    outcome: InterviewOutcome | None = None
    application: CalendarApplication | None = Field(
        description="`null` en un recordatorio que no va ligado a ninguna solicitud."
    )


class CalendarEventsRead(BaseModel):
    events: list[CalendarEvent] = Field(description="Ordenados por `starts_at`.")
