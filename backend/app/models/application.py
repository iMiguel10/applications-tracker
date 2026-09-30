import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.constraints import enum_check
from app.domain.application import (
    DEFAULT_CURRENCY,
    MAX_JOB_DESCRIPTION_LENGTH,
    MAX_NOTES_LENGTH,
    ApplicationOrigin,
    ApplicationSource,
    Currency,
    WorkMode,
)
from app.domain.application_status import (
    STATUSES_WITHOUT_APPLIED_AT,
    ApplicationStatus,
)

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.document import Document

_STATUSES_WITHOUT_APPLIED_AT_SQL = ", ".join(
    f"'{status.value}'" for status in sorted(STATUSES_WITHOUT_APPLIED_AT)
)


class Application(Base):
    """Solicitud a un puesto (arquitectura §5, la tabla que hay que acertar a la primera)."""

    __tablename__ = "applications"
    __table_args__ = (
        # La empresa debe ser del MISMO usuario: la BD lo impone aunque el código
        # olvide comprobarlo (A9). RESTRICT: no se borra una empresa con solicitudes.
        ForeignKeyConstraint(
            ["company_id", "user_id"],
            ["companies.id", "companies.user_id"],
            ondelete="RESTRICT",
        ),
        # El CV y la carta enviados (RF-28), documentos del MISMO usuario. NO ACTION y
        # no RESTRICT: RESTRICT se comprueba en el acto y haría fallar el borrado de
        # la cuenta, que borra en cascada solicitudes y documentos en la misma
        # sentencia; NO ACTION espera al final de la sentencia. Borrar un documento
        # en uso por separado sigue fallando (y el service lo avisa antes, RF-93).
        ForeignKeyConstraint(
            ["cv_document_id", "user_id"],
            ["documents.id", "documents.user_id"],
        ),
        ForeignKeyConstraint(
            ["cover_letter_document_id", "user_id"],
            ["documents.id", "documents.user_id"],
        ),
        CheckConstraint(
            f"char_length(job_description) <= {MAX_JOB_DESCRIPTION_LENGTH}",
            name="job_description_length",
        ),
        # "Usado en" de cada documento y la comprobación de la FK al borrarlo.
        Index(
            "ix_applications_cv_document_id",
            "cv_document_id",
            postgresql_where=text("cv_document_id IS NOT NULL"),
        ),
        Index(
            "ix_applications_cover_letter_document_id",
            "cover_letter_document_id",
            postgresql_where=text("cover_letter_document_id IS NOT NULL"),
        ),
        # Destino de la FK compuesta de reminders (F4).
        UniqueConstraint("id", "user_id"),
        enum_check("status", ApplicationStatus, "status"),
        enum_check("work_mode", WorkMode, "work_mode"),
        enum_check("source", ApplicationSource, "source"),
        enum_check("origin", ApplicationOrigin, "origin"),
        CheckConstraint(
            f"status IN ({_STATUSES_WITHOUT_APPLIED_AT_SQL}) OR applied_at IS NOT NULL",
            name="applied_at_required",
        ),
        CheckConstraint("salary_min >= 0", name="salary_min_non_negative"),
        CheckConstraint("salary_max >= 0", name="salary_max_non_negative"),
        CheckConstraint("salary_min <= salary_max", name="salary_range"),
        enum_check("salary_currency", Currency, "salary_currency"),
        CheckConstraint(
            f"char_length(notes) <= {MAX_NOTES_LENGTH}", name="notes_length"
        ),
        Index("ix_applications_user_id_status", "user_id", "status"),
        Index("ix_applications_user_id_applied_at", "user_id", text("applied_at DESC")),
        # También cubre la FK compuesta (company_id, user_id).
        Index("ix_applications_user_id_company_id", "user_id", "company_id"),
        Index(
            "ix_applications_user_id_last_activity_at", "user_id", "last_activity_at"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    company_id: Mapped[uuid.UUID]

    position_title: Mapped[str] = mapped_column(String(200))
    job_url: Mapped[str | None] = mapped_column(String(2000))
    location: Mapped[str | None] = mapped_column(String(200))
    work_mode: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str | None] = mapped_column(String(30))
    origin: Mapped[str] = mapped_column(
        String(30), server_default=ApplicationOrigin.MANUAL.value
    )

    # Copia del último cambio del historial (arquitectura §4). En F2 solo se fija al
    # crear; desde F3 la escribe únicamente ApplicationStatusService.
    status: Mapped[str] = mapped_column(String(20))
    applied_at: Mapped[date | None] = mapped_column(Date)

    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(
        String(3), server_default=DEFAULT_CURRENCY.value
    )

    notes: Mapped[str | None] = mapped_column(Text)
    # RF-27: el texto del anuncio, pegado por el usuario. Entrada de la IA (F15).
    job_description: Mapped[str | None] = mapped_column(Text)
    cv_document_id: Mapped[uuid.UUID | None] = mapped_column()
    cover_letter_document_id: Mapped[uuid.UUID | None] = mapped_column()
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Alimenta el aviso "sin actividad" (RF-64). La actualizan los services al
    # cambiar de estado (F3) o tocar entrevistas (F4), no al editar datos.
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.clock_timestamp(),
        onupdate=func.clock_timestamp(),
    )

    # lazy="raise": en async no hay carga implícita; cada consulta declara lo que carga.
    company: Mapped["Company"] = relationship(
        back_populates="applications",
        lazy="raise",
    )
    # Solo lectura: se asignan por id. primaryjoin explícito porque las dos FK a
    # documents comparten user_id.
    cv_document: Mapped["Document | None"] = relationship(
        primaryjoin="Application.cv_document_id == Document.id",
        foreign_keys=[cv_document_id],
        lazy="raise",
        viewonly=True,
    )
    cover_letter_document: Mapped["Document | None"] = relationship(
        primaryjoin="Application.cover_letter_document_id == Document.id",
        foreign_keys=[cover_letter_document_id],
        lazy="raise",
        viewonly=True,
    )
