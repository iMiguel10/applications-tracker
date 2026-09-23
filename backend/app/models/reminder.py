import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.reminder import ReminderChannel, ReminderStatus

if TYPE_CHECKING:
    from app.models.application import Application


class Reminder(Base):
    """Recordatorio de un usuario, opcionalmente ligado a una solicitud (arquitectura
    §5, RF-50…53). Raíz de propiedad `user_id`, no una tabla hija de `applications`:
    la costura para un futuro listado o dashboard cruzado entre solicitudes."""

    __tablename__ = "reminders"
    __table_args__ = (
        # FK compuesta opcional (A9): si application_id no es NULL, tiene que ser una
        # solicitud del MISMO usuario. Con MATCH SIMPLE (por defecto), un NULL en
        # application_id no se comprueba: se puede crear sin solicitud asociada.
        ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            ondelete="CASCADE",
        ),
        enum_check("channel", ReminderChannel, "channel"),
        enum_check("status", ReminderStatus, "status"),
        # Parcial: solo los pendientes son relevantes para "qué hay que hacer" (RF-52).
        Index(
            "ix_reminders_user_id_due_at_pending",
            "user_id",
            "due_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column()

    title: Mapped[str] = mapped_column(String(200))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Costura para canales reales (RF-53): en el MVP nunca se rellena, in_app no envía.
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(
        String(20), server_default=ReminderChannel.IN_APP.value
    )
    status: Mapped[str] = mapped_column(
        String(20), server_default=ReminderStatus.PENDING.value
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )

    # lazy="raise": cada consulta declara si necesita el resumen de la solicitud.
    application: Mapped["Application | None"] = relationship(lazy="raise")
