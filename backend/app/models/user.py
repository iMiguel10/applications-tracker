import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    SmallInteger,
    String,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.dashboard import STALE_AFTER_DAYS
from app.domain.notifications import (
    DEFAULT_INTERVIEW_NOTICE_HOURS,
    MAX_INTERVIEW_NOTICE_HOURS,
    MIN_INTERVIEW_NOTICE_HOURS,
)
from app.domain.user import (
    MAX_STALE_AFTER_DAYS,
    MAX_TIMEZONE_LENGTH,
    MIN_STALE_AFTER_DAYS,
    Language,
)


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
        CheckConstraint(
            "interview_notice_hours BETWEEN "
            f"{MIN_INTERVIEW_NOTICE_HOURS} AND {MAX_INTERVIEW_NOTICE_HOURS}",
            name="interview_notice_hours_range",
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
    # F11 (RF-07, A39): zona IANA. NULL hasta que el frontend la detecta; quien la
    # necesite (los emails de F12) usa UTC mientras tanto. Sin CHECK: la lista de
    # zonas cambia con tzdata y la valida la aplicación (domain/user.py).
    timezone: Mapped[str | None] = mapped_column(String(MAX_TIMEZONE_LENGTH))

    # F12 (RF-84): cada tipo de aviso por email se activa por separado. Por
    # defecto, los dos que responden a algo que el usuario creó (su recordatorio,
    # su entrevista); los otros dos, apagados para no llenar la bandeja sin pedirlo.
    notify_reminder_due: Mapped[bool] = mapped_column(Boolean, server_default=true())
    notify_interview: Mapped[bool] = mapped_column(Boolean, server_default=true())
    notify_weekly_digest: Mapped[bool] = mapped_column(Boolean, server_default=false())
    notify_stale: Mapped[bool] = mapped_column(Boolean, server_default=false())
    # RF-81: cuántas horas antes de una entrevista llega su aviso.
    interview_notice_hours: Mapped[int] = mapped_column(
        SmallInteger, server_default=str(DEFAULT_INTERVIEW_NOTICE_HOURS)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
