import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.application import MAX_NOTES_LENGTH
from app.domain.interview import InterviewFormat, InterviewOutcome, InterviewType


class Interview(Base):
    """Entrevista de una solicitud (arquitectura §5, RF-40…42). Editable (a
    diferencia del historial de estados): tiene `updated_at`."""

    __tablename__ = "interviews"
    __table_args__ = (
        enum_check("interview_type", InterviewType, "interview_type"),
        enum_check("format", InterviewFormat, "format"),
        enum_check("outcome", InterviewOutcome, "outcome"),
        CheckConstraint(
            f"char_length(notes) <= {MAX_NOTES_LENGTH}", name="notes_length"
        ),
        CheckConstraint("duration_minutes > 0", name="duration_minutes_positive"),
        Index(
            "ix_interviews_application_id_scheduled_at",
            "application_id",
            "scheduled_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    interviewers: Mapped[str | None] = mapped_column(String(500))
    interview_type: Mapped[str | None] = mapped_column(String(20))
    format: Mapped[str | None] = mapped_column(String(20))
    # Resultado (RF-41); se registra por separado de la creación.
    outcome: Mapped[str] = mapped_column(
        String(20), server_default=InterviewOutcome.PENDING.value
    )
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )
