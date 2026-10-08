import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import values_check
from app.domain.ai import PERSONAL_PROVIDERS


class AiProviderKey(Base):
    """La clave de API de un usuario para un proveedor (RF-151, ia.md §7), cifrada
    con `MultiFernet`. Nunca se guarda ni se devuelve en claro: solo sus 4 últimos
    caracteres, para reconocerla. Una por proveedor, con el modelo elegido de la
    lista que permite quien despliega (`AI_*_MODELS`)."""

    __tablename__ = "ai_provider_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "provider"),
        values_check("provider", PERSONAL_PROVIDERS, "provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(String(30))
    # Sin CHECK: la lista de modelos permitidos es configuración y cambia sin
    # migración. Si un modelo deja de permitirse, la clave sigue y el usuario
    # elige otro (decisión 0017).
    model: Mapped[str] = mapped_column(String(100))
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    last4: Mapped[str] = mapped_column(String(4))
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )

    def __repr__(self) -> str:
        # Ni el texto cifrado en un log.
        return f"AiProviderKey(provider={self.provider!r}, last4={self.last4!r})"
