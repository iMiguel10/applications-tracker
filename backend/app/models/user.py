import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.dashboard import STALE_AFTER_DAYS
from app.domain.user import MAX_STALE_AFTER_DAYS, MIN_STALE_AFTER_DAYS, Language


class User(Base):
    """Enlace con el usuario de SuperTokens (arquitectura §4, decisión A12).

    No copia datos de identidad (email, nombre): se piden a SuperTokens cuando
    hacen falta. Existe para las FKs y el ON DELETE CASCADE de los datos propios.
    """

    __tablename__ = "users"
    __table_args__ = (
        enum_check("language", Language, "language"),
        CheckConstraint(
            f"stale_after_days BETWEEN {MIN_STALE_AFTER_DAYS} AND {MAX_STALE_AFTER_DAYS}",
            name="stale_after_days_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    supertokens_user_id: Mapped[str] = mapped_column(String(128), unique=True)

    # F8: preferencias. `language` NULL sigue el idioma del navegador (comportamiento
    # de siempre); solo se fija si el usuario elige uno explícitamente.
    language: Mapped[str | None] = mapped_column(String(2))
    stale_after_days: Mapped[int] = mapped_column(
        SmallInteger, server_default=str(STALE_AFTER_DAYS)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
