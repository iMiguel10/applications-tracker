import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.application import MAX_NOTES_LENGTH
from app.domain.application_status import ApplicationStatus


class ApplicationStatusChange(Base):
    """Historial append-only de cambios de estado (arquitectura §5). La fila nunca se
    edita ni se borra salvo al deshacer el último cambio: sin `updated_at`.

    `seq` es el orden real del historial (decisión 0004), no `created_at` ni
    `changed_at`. Ver la nota "Una secuencia y dos fechas" en la arquitectura.
    """

    __tablename__ = "application_status_changes"
    __table_args__ = (
        enum_check("from_status", ApplicationStatus, "from_status"),
        enum_check("to_status", ApplicationStatus, "to_status"),
        CheckConstraint(f"char_length(note) <= {MAX_NOTES_LENGTH}", name="note_length"),
        Index(
            "ix_application_status_changes_application_id_seq",
            "application_id",
            text("seq DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
    )
    # NULL solo en el cambio inicial que crea la solicitud.
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    # Fecha declarada por el usuario (por defecto, ahora): "cuándo ocurrió de verdad".
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    # "Cuándo se registró en el sistema": informativo, NUNCA para ordenar (0001, 0004).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
    # El orden real del historial (0004): siempre creciente, ajeno al reloj. Único por
    # tabla, no por solicitud: nunca se muestra como "cambio número N".
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True)
