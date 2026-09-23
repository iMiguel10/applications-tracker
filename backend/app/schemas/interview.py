import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.interview import InterviewFormat, InterviewOutcome, InterviewType
from app.schemas.common import OptionalMediumText, OptionalNotes

Duration = Annotated[int, Field(ge=1, le=1440, description="Minutos.")]


class InterviewCreate(BaseModel):
    scheduled_at: AwareDatetime = Field(description="Fecha y hora de la entrevista.")
    duration_minutes: Duration | None = None
    interviewers: OptionalMediumText = Field(
        default=None, description="Con quién.", examples=["Laura (RR. HH.)"]
    )
    interview_type: InterviewType | None = None
    format: InterviewFormat | None = None
    notes: OptionalNotes = Field(default=None, description="Máximo 5 000 caracteres.")


class InterviewUpdate(BaseModel):
    """Actualización parcial: solo se modifican los campos enviados; `null` vacía un
    campo opcional. Incluye `outcome`: es como se registra el resultado (RF-41)."""

    scheduled_at: AwareDatetime | None = None
    duration_minutes: Duration | None = None
    interviewers: OptionalMediumText = None
    interview_type: InterviewType | None = None
    format: InterviewFormat | None = None
    outcome: InterviewOutcome | None = None
    notes: OptionalNotes = None


class InterviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int | None
    interviewers: str | None
    interview_type: InterviewType | None
    format: InterviewFormat | None
    outcome: InterviewOutcome
    notes: str | None
    created_at: datetime
    updated_at: datetime
