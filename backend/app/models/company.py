import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.application import MAX_NOTES_LENGTH

if TYPE_CHECKING:
    from app.models.application import Application


class Company(Base):
    """Empresa de un usuario (arquitectura §5). Reutilizable entre solicitudes."""

    __tablename__ = "companies"
    __table_args__ = (
        # Destino de la FK compuesta de applications: garantiza en la BD que una
        # solicitud solo puede apuntar a una empresa del mismo usuario (A9).
        UniqueConstraint("id", "user_id"),
        # "Acme" y "acme" son la misma empresa para un usuario (RF-10).
        Index(
            "uq_companies_user_id_lower_name",
            "user_id",
            func.lower(text("name")),
            unique=True,
        ),
        CheckConstraint(
            f"char_length(notes) <= {MAX_NOTES_LENGTH}", name="notes_length"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(200))
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

    # lazy="raise": en async no hay carga implícita; cada consulta declara lo que carga.
    applications: Mapped[list["Application"]] = relationship(
        back_populates="company",
        lazy="raise",
    )
