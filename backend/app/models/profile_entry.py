import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
    func,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.profile import (
    BULLET_MAX_LENGTH,
    ENTRY_DESCRIPTION_MAX_LENGTH,
    ENTRY_LOCATION_MAX_LENGTH,
    ENTRY_ORGANIZATION_MAX_LENGTH,
    ENTRY_TITLE_MAX_LENGTH,
    EntryKind,
)


class ProfileEntry(Base):
    """Una experiencia, formación, proyecto o certificación del perfil (RF-101,
    RF-102, A26). Hija de `profiles`, sin `user_id` propio: el repository filtra
    con un join a `profiles.user_id` (invariante 1), como las entrevistas."""

    __tablename__ = "profile_entries"
    __table_args__ = (
        enum_check("kind", EntryKind, "kind"),
        # "Actualidad" no tiene fecha de fin.
        CheckConstraint(
            "NOT (is_current AND end_date IS NOT NULL)", name="current_has_no_end"
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="end_after_start",
        ),
        CheckConstraint(
            f"char_length(description) <= {ENTRY_DESCRIPTION_MAX_LENGTH}",
            name="description_length",
        ),
        Index("ix_profile_entries_profile_id_kind", "profile_id", "kind", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=sql_text("gen_random_uuid()"),
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(20))
    # Puesto, título académico, nombre del proyecto o de la certificación.
    title: Mapped[str] = mapped_column(String(ENTRY_TITLE_MAX_LENGTH))
    organization: Mapped[str | None] = mapped_column(
        String(ENTRY_ORGANIZATION_MAX_LENGTH)
    )
    location: Mapped[str | None] = mapped_column(String(ENTRY_LOCATION_MAX_LENGTH))
    # Un CV muestra mes y año: la interfaz guarda el día 1 del mes.
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=false())
    description: Mapped[str | None] = mapped_column(Text)
    # Orden dentro de su sección. Sin UNIQUE: reordenar reescribe todas las
    # posiciones de la sección a la vez.
    position: Mapped[int] = mapped_column(Integer)

    bullets: Mapped[list["ProfileEntryBullet"]] = relationship(
        order_by="ProfileEntryBullet.position",
        cascade="all, delete-orphan",
        lazy="raise",
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


class ProfileEntryBullet(Base):
    """Un logro de una entrada. En F15 la IA los reformula y los referencia por su
    id: editar una entrada conserva el id de los logros que siguen en ella."""

    __tablename__ = "profile_entry_bullets"
    __table_args__ = (
        CheckConstraint(
            f"char_length(text) BETWEEN 1 AND {BULLET_MAX_LENGTH}", name="text_length"
        ),
        Index("ix_profile_entry_bullets_entry_id", "entry_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=sql_text("gen_random_uuid()"),
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile_entries.id", ondelete="CASCADE")
    )
    text: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
