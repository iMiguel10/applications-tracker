import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.application_status import ApplicationStatus
from app.domain.interview import InterviewFormat, InterviewType
from app.schemas.company import CompanySummary
from app.schemas.reminder import ReminderRead


class ApplicationSummary(BaseModel):
    """Lo mínimo para identificar una solicitud desde un widget del dashboard; el
    detalle completo está a un clic (RF-23)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position_title: str = Field(examples=["Backend Developer"])
    company: CompanySummary
    status: ApplicationStatus


class StatusCount(BaseModel):
    """RF-60."""

    status: ApplicationStatus
    count: int


class WeeklyApplications(BaseModel):
    """RF-61. `week_start` es el lunes de esa semana ISO."""

    week_start: date
    count: int


class ResponseRate(BaseModel):
    """RF-62 y RF-66: siempre se indica sobre cuántas solicitudes se calcula, y
    `rate` es `null` con una base menor que `MIN_SAMPLE_FOR_RATE` (RF-66)."""

    sent_count: int
    reached_count: int
    rate: float | None = Field(
        description="Proporción entre 0 y 1, o `null` si `sent_count` es demasiado "
        "pequeño para ser representativo."
    )


class UpcomingInterview(BaseModel):
    """RF-63."""

    id: uuid.UUID
    scheduled_at: datetime
    interview_type: InterviewType | None
    format: InterviewFormat | None
    application: ApplicationSummary


class StaleApplication(BaseModel):
    """RF-64."""

    application: ApplicationSummary
    last_activity_at: datetime
    days_since_activity: int


class DashboardRead(BaseModel):
    status_counts: list[StatusCount]
    applications_per_week: list[WeeklyApplications]
    response_rate: ResponseRate

    upcoming_interviews: list[UpcomingInterview]
    upcoming_interviews_total: int = Field(
        description="Total de próximas entrevistas; la lista solo trae un vistazo."
    )
    pending_reminders: list[ReminderRead]
    pending_reminders_total: int = Field(
        description="Total de recordatorios pendientes o vencidos; la lista solo "
        "trae un vistazo. El listado completo, con acciones, vive en /reminders."
    )
    stale_applications: list[StaleApplication]
    stale_applications_total: int = Field(
        description="Total de solicitudes sin actividad; la lista solo trae un vistazo."
    )
    stale_after_days: int = Field(
        description="Días sin actividad a partir de los cuales una solicitud entra "
        "en `stale_applications` (RF-64)."
    )
