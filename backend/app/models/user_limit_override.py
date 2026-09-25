import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.limits import LimitKey, keys_allowing_unlimited

_UNLIMITED_KEYS = ", ".join(f"'{key.value}'" for key in keys_allowing_unlimited())


class UserLimitOverride(Base):
    """Excepción de un límite para una cuenta concreta (RF-143). Sin fila, vale el
    global de la configuración. Se ajusta con scripts/set_user_limit.py: la
    administración no tiene interfaz.

    `value` NULL es "sin límite", y solo se admite en los límites que lo permiten
    (`LimitRule.allows_unlimited`). La BD lo impone también: un límite nuevo con
    coste (almacenamiento, IA) queda fuera de la lista y no puede quedar libre
    aunque el código se equivocara."""

    __tablename__ = "user_limit_overrides"
    __table_args__ = (
        enum_check("limit_key", LimitKey, "limit_key"),
        CheckConstraint("value >= 0", name="value_not_negative"),
        CheckConstraint(
            f"value IS NOT NULL OR limit_key IN ({_UNLIMITED_KEYS})",
            name="unlimited_only_where_allowed",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    limit_key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int | None] = mapped_column(Integer)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )
