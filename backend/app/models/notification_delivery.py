import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.notifications import DeliveryStatus, NotificationKind


class NotificationDelivery(Base):
    """Un email de aviso: lo que hace posible "nunca dos veces" (RF-87, A20).

    Se inserta en `claimed` y se confirma ANTES de hablar con el SMTP. La clave
    única (usuario, tipo, motivo) hace que dos barridos que compiten por el mismo
    aviso inserten una sola fila: el segundo no reclama nada y no envía nada.
    """

    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "dedupe_key"),
        enum_check("kind", NotificationKind, "kind"),
        enum_check("status", DeliveryStatus, "status"),
        # Barrido de reclamos abandonados (cada 5 min): solo mira los `claimed`.
        Index(
            "ix_notification_deliveries_claimed_at_claimed",
            "claimed_at",
            postgresql_where=text("status = 'claimed'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(30))
    # Qué hace único el motivo: `reminder:<id>`, `interview:<id>:<scheduled_at>`…
    # (segundo plano §4).
    dedupe_key: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    # Último reclamo: el barrido de abandonados mide desde aquí.
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Solo en `failed` con intentos restantes: desde cuándo se puede reintentar.
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
