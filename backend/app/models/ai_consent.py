import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.ai import AiProvider


class AiConsent(Base):
    """Consentimiento para enviar datos del perfil a un proveedor de IA (RF-116,
    RF-154, ia.md §8). Uno por proveedor: dar el consentimiento a Groq no lo da a
    OpenAI. Está vigente si no se ha retirado y se dio sobre la versión actual del
    texto (`AI_CONSENT_VERSION`): si el texto cambia, se vuelve a pedir."""

    __tablename__ = "ai_consents"
    __table_args__ = (
        UniqueConstraint("user_id", "provider"),
        enum_check("provider", AiProvider, "provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(String(30))
    text_version: Mapped[int] = mapped_column(Integer)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
