import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.ai import (
    STATUSES_WITH_ERROR,
    AiProvider,
    AiTask,
    KeySource,
    ProposalErrorCode,
    ProposalLanguage,
    ProposalStatus,
)

_WITH_ERROR = ", ".join(f"'{status.value}'" for status in STATUSES_WITH_ERROR)


class AiProposal(Base):
    """Cada uso de la IA (RF-110…119, v2 §4). Es también el **registro de consumo**:
    la cuota gratuita se cuenta sobre esta tabla, sin contadores aparte que puedan
    desincronizarse.

    `billable` se pone a true en cuanto el proveedor respondió, pase o no la
    validación: eso es lo que gasta un uso (ia.md §6). El proveedor, el modelo y la
    versión del prompt se guardan como texto: aunque un modelo se retire de la
    configuración, se sigue sabiendo con qué se hizo cada propuesta (RF-115, 0017).
    """

    __tablename__ = "ai_proposals"
    __table_args__ = (
        # La solicitud es del MISMO usuario. Borrarla borra sus propuestas.
        ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            ondelete="CASCADE",
        ),
        enum_check("kind", AiTask, "kind"),
        enum_check("status", ProposalStatus, "status"),
        enum_check("key_source", KeySource, "key_source"),
        enum_check("provider", AiProvider, "provider"),
        enum_check("error_code", ProposalErrorCode, "error_code"),
        enum_check("language", ProposalLanguage, "language"),
        CheckConstraint(
            f"(status IN ({_WITH_ERROR})) = (error_code IS NOT NULL)",
            name="error_code_only_when_unsuccessful",
        ),
        CheckConstraint(
            "(status = 'succeeded') = (proposal IS NOT NULL)",
            name="proposal_only_when_succeeded",
        ),
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND cost_micros >= 0",
            name="usage_not_negative",
        ),
        # La cuota gratuita (A30): lo de la plataforma, por usuario y tarea.
        Index(
            "ix_ai_proposals_platform_usage",
            "user_id",
            "kind",
            postgresql_where=text("key_source = 'platform'"),
        ),
        Index("ix_ai_proposals_application_created", "application_id", "created_at"),
        # El barrido de las que se quedaron en cola o en curso.
        Index(
            "ix_ai_proposals_in_flight_updated_at",
            "updated_at",
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    application_id: Mapped[uuid.UUID] = mapped_column()
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    key_source: Mapped[str] = mapped_column(String(10))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(30))
    # Idioma en que se escribe la propuesta.
    language: Mapped[str] = mapped_column(String(2))
    billable: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    input_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    # Millonésimas de dólar, con el precio de la configuración (solo informativo).
    cost_micros: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    # La propuesta validada (CvProposal), con los UUID reales. Solo en `succeeded`.
    proposal: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    error_code: Mapped[str | None] = mapped_column(String(50))
    # Cuándo la tomó el worker: el barrido da por colgadas las que llevan demasiado.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )
