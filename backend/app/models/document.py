import uuid
from datetime import datetime
from typing import Any

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.documents import (
    NAME_MAX_LENGTH,
    TEMPLATE_MAX_LENGTH,
    DocumentErrorCode,
    DocumentKind,
    DocumentOrigin,
    DocumentStatus,
)


class Document(Base):
    """Un CV o una carta de la biblioteca (RF-90…94, v2 §2).

    Postgres manda (invariante 9 de v2): la fila se confirma DESPUÉS de escribir el
    fichero, así que solo pueden sobrar ficheros, nunca faltar (ficheros §5).

    Los generados (F14) guardan su diseño, el idioma de las etiquetas y la foto
    fija de lo que se maquetó (`content`, A27). La columna de los adaptados con IA
    (`ai_proposal_id`) llega con F15.
    """

    __tablename__ = "documents"
    __table_args__ = (
        # Destino de las FK compuestas de applications (F13, paso 5): el CV enviado
        # tiene que ser un documento del MISMO usuario.
        UniqueConstraint("id", "user_id"),
        # Una clave, un documento. Y el índice con que el barrido de huérfanos busca
        # en lote qué claves del almacén tienen fila (ficheros §5).
        UniqueConstraint("storage_key"),
        enum_check("kind", DocumentKind, "kind"),
        enum_check("origin", DocumentOrigin, "origin"),
        enum_check("status", DocumentStatus, "status"),
        CheckConstraint(
            "status <> 'ready' OR storage_key IS NOT NULL",
            name="ready_has_storage_key",
        ),
        CheckConstraint("size_bytes >= 0", name="size_not_negative"),
        enum_check("error_code", DocumentErrorCode, "error_code"),
        # Un generado sin su foto fija no se podría maquetar ni reintentar, y un
        # subido no tiene diseño ni contenido que guardar. Nunca a medias: con
        # uno de los tres, los tres.
        CheckConstraint(
            "(origin = 'uploaded' AND "
            "template IS NULL AND language IS NULL AND content IS NULL) OR "
            "(origin <> 'uploaded' AND "
            "template IS NOT NULL AND language IS NOT NULL AND content IS NOT NULL)",
            name="content_matches_origin",
        ),
        # El motivo del fallo, solo en los fallidos: reintentar lo borra.
        CheckConstraint(
            "(status = 'failed') = (error_code IS NOT NULL)",
            name="error_code_only_when_failed",
        ),
        # Los pendientes que el barrido reencola (segundo plano §3). Por
        # `updated_at`: reintentar un fallido lo vuelve a poner `pending`.
        Index(
            "ix_documents_pending_updated_at",
            "updated_at",
            postgresql_where=text("status = 'pending'"),
        ),
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
    # Solo en los generados (F14): diseño, idioma de las etiquetas y foto fija.
    template: Mapped[str | None] = mapped_column(String(TEMPLATE_MAX_LENGTH))
    language: Mapped[str | None] = mapped_column(String(2))
    # `none_as_null`: sin él, `None` se guarda como el JSON `null`, que no es
    # `NULL` para SQL, y el CHECK `content_matches_origin` no lo vería.
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    # Por qué falló, solo en los fallidos (DocumentErrorCode).
    error_code: Mapped[str | None] = mapped_column(String(50))
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
