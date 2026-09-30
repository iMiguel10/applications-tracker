import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.documents import (
    NAME_MAX_LENGTH,
    DocumentKind,
    DocumentOrigin,
    DocumentStatus,
)


class Document(Base):
    """Un CV o una carta de la biblioteca (RF-90…94, v2 §2).

    Postgres manda (invariante 9 de v2): la fila se confirma DESPUÉS de escribir el
    fichero, así que solo pueden sobrar ficheros, nunca faltar (ficheros §5).

    Las columnas de los documentos generados (`template`, `language`, `content`) y
    de los adaptados con IA (`ai_proposal_id`) llegan con F14 y F15.
    """

    __tablename__ = "documents"
    __table_args__ = (
        # Destino de las FK compuestas de applications (F13, paso 5): el CV enviado
        # tiene que ser un documento del MISMO usuario.
        UniqueConstraint("id", "user_id"),
        enum_check("kind", DocumentKind, "kind"),
        enum_check("origin", DocumentOrigin, "origin"),
        enum_check("status", DocumentStatus, "status"),
        CheckConstraint(
            "status <> 'ready' OR storage_key IS NOT NULL",
            name="ready_has_storage_key",
        ),
        CheckConstraint("size_bytes >= 0", name="size_not_negative"),
        Index("ix_documents_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(20))
    origin: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    # Nombre visible: el original del fichero, saneado. Solo se muestra.
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    # NULL mientras está `pending`. Generada por el servidor (A23).
    storage_key: Mapped[str | None] = mapped_column(String(300))
    # Bytes escritos de verdad, no los que declaró el cliente. Su suma es el
    # almacenamiento usado.
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    # RF-93: archivar oculta sin romper la asociación con las solicitudes.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )
