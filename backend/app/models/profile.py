import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.profile import (
    CONTACT_EMAIL_MAX_LENGTH,
    FULL_NAME_MAX_LENGTH,
    HEADLINE_MAX_LENGTH,
    LOCATION_MAX_LENGTH,
    PHONE_MAX_LENGTH,
    SUMMARY_MAX_LENGTH,
)


class Profile(Base):
    """Perfil profesional, uno por usuario (RF-100, A26).

    La fila se crea al guardarlo por primera vez: hasta entonces el perfil existe
    vacío para la API, sin fila. Las experiencias, la formación, las habilidades y
    los idiomas cuelgan de aquí en tablas propias (F14, pasos 2 y 3).
    """

    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint(
            f"char_length(summary) <= {SUMMARY_MAX_LENGTH}", name="summary_length"
        ),
        CheckConstraint("jsonb_typeof(links) = 'array'", name="links_is_array"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    # Datos de contacto del CV. No son los de la cuenta (invariante 9: `users` no
    # copia la identidad): el email de contacto puede ser otro.
    full_name: Mapped[str | None] = mapped_column(String(FULL_NAME_MAX_LENGTH))
    headline: Mapped[str | None] = mapped_column(String(HEADLINE_MAX_LENGTH))
    contact_email: Mapped[str | None] = mapped_column(String(CONTACT_EMAIL_MAX_LENGTH))
    phone: Mapped[str | None] = mapped_column(String(PHONE_MAX_LENGTH))
    location: Mapped[str | None] = mapped_column(String(LOCATION_MAX_LENGTH))
    # Lista de {label, url}. Una lista corta que siempre se lee y se guarda entera:
    # una tabla aparte no aportaría nada (A26).
    links: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    summary: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )
