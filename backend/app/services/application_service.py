import csv
import io
import uuid
from datetime import UTC, date, datetime
from typing import Any, NoReturn, cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundError
from app.domain.application import ApplicationOrigin
from app.domain.application_status import (
    STATUSES_WITHOUT_APPLIED_AT,
    ApplicationStatus,
)
from app.domain.documents import DocumentKind
from app.domain.limits import LimitKey
from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.models.document import Document
from app.repositories.application_repository import (
    ApplicationFilters,
    ApplicationRepository,
    ApplicationSort,
)
from app.repositories.application_status_change_repository import (
    ApplicationStatusChangeRepository,
)
from app.repositories.company_repository import CompanyRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListQuery,
    ApplicationUpdate,
)
from app.services.limit_service import LimitService

# Nombres de las FK compuestas de applications a documents (naming_convention).
_DOCUMENT_FOREIGN_KEYS = (
    "fk_applications_cv_document_id_documents",
    "fk_applications_cover_letter_document_id_documents",
)

_ARCHIVED_FILTER: dict[str, bool | None] = {
    "active": False,
    "archived": True,
    "all": None,
}


class ApplicationService:
    """Reglas de negocio de las solicitudes. Dueño de la transacción: es quien hace commit.

    El estado NO se cambia aquí: solo se fija al crear (saved/applied), junto con el
    cambio inicial de su historial (arquitectura §4). Cambiar de estado, deshacer y
    leer el historial son ApplicationStatusService.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.applications = ApplicationRepository(session)
        self.companies = CompanyRepository(session)
        self.documents = DocumentRepository(session)
        self.status_changes = ApplicationStatusChangeRepository(session)
        self.limits = LimitService(session)

    async def list(
        self, user_id: uuid.UUID, query: ApplicationListQuery
    ) -> tuple[list[Application], int]:
        filters = ApplicationFilters(
            statuses=[status.value for status in query.status],
            company_id=query.company_id,
            work_modes=[mode.value for mode in query.work_mode],
            sources=[source.value for source in query.source],
            applied_from=query.applied_from,
            applied_to=query.applied_to,
            search=query.q,
            archived=_ARCHIVED_FILTER[query.archived],
        )
        return await self.applications.list(
            user_id,
            filters,
            page=query.page,
            limit=query.limit,
            sort_by=cast(ApplicationSort, query.sort_by),
            descending=query.order == "desc",
        )

    async def get(self, user_id: uuid.UUID, application_id: uuid.UUID) -> Application:
        application = await self.applications.get(user_id, application_id)
        if application is None:
            raise NotFoundError("Application")
        return application

    async def create(self, user_id: uuid.UUID, data: ApplicationCreate) -> Application:
        await self.limits.check(user_id, LimitKey.APPLICATIONS)
        # La empresa debe existir y ser del usuario (T3). Si es de otro, 404 igual
        # que si no existiera; la FK compuesta lo impediría de todos modos.
        await self._ensure_company(user_id, data.company_id)
        await self._ensure_documents(
            user_id, data.cv_document_id, data.cover_letter_document_id
        )

        fields = data.model_dump()
        if (
            fields["status"] == ApplicationStatus.APPLIED
            and fields["applied_at"] is None
        ):
            fields["applied_at"] = _today_utc()

        application = Application(
            user_id=user_id, origin=ApplicationOrigin.MANUAL.value, **fields
        )
        try:
            await self.applications.add(application)
            # Invariante 4: ninguna solicitud existe sin su cambio inicial en el
            # historial (arquitectura §4). from_status NULL lo distingue de un
            # cambio real.
            await self.status_changes.add(
                ApplicationStatusChange(
                    application_id=application.id,
                    from_status=None,
                    to_status=application.status,
                    changed_at=datetime.now(UTC),
                )
            )
            await self.session.commit()
        except IntegrityError as error:
            await self._raise_document_gone_or_reraise(error)
        # Recarga con la empresa (la relación es lazy="raise").
        return await self.get(user_id, application.id)

    async def update(
        self, user_id: uuid.UUID, application_id: uuid.UUID, data: ApplicationUpdate
    ) -> Application:
        application = await self.get(user_id, application_id)
        # Solo los campos enviados: distinguir "no enviado" de null (vaciar).
        changes: dict[str, Any] = data.model_dump(exclude_unset=True)

        if "position_title" in changes and changes["position_title"] is None:
            raise AppException(
                "Position title cannot be empty",
                status_code=422,
                code="position_title_required",
            )
        if "company_id" in changes:
            if changes["company_id"] is None:
                raise AppException(
                    "Company cannot be empty", status_code=422, code="company_required"
                )
            await self._ensure_company(user_id, changes["company_id"])
        if "salary_currency" in changes and changes["salary_currency"] is None:
            del changes["salary_currency"]
        await self._ensure_documents(
            user_id,
            changes.get("cv_document_id"),
            changes.get("cover_letter_document_id"),
        )

        # Reglas que dependen de varios campos: se validan sobre el resultado de
        # mezclar lo guardado con lo enviado. El schema solo ve lo enviado: un
        # PATCH {"salary_min": 90000} no sabe que salary_max guardado es 50000.
        merged = {
            "status": application.status,
            "applied_at": application.applied_at,
            "salary_min": application.salary_min,
            "salary_max": application.salary_max,
        } | changes
        _validate_merged(merged)

        for field, value in changes.items():
            setattr(application, field, value)
        try:
            await self.applications.save(application)
            await self.session.commit()
        except IntegrityError as error:
            await self._raise_document_gone_or_reraise(error)
        return await self.get(user_id, application_id)

    async def archive(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application:
        application = await self.get(user_id, application_id)
        # Idempotente: archivar dos veces conserva la fecha del primer archivado.
        if application.archived_at is None:
            application.archived_at = datetime.now(UTC)
            await self.applications.save(application)
            await self.session.commit()
        return application

    async def unarchive(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application:
        application = await self.get(user_id, application_id)
        if application.archived_at is not None:
            application.archived_at = None
            await self.applications.save(application)
            await self.session.commit()
        return application

    async def delete(self, user_id: uuid.UUID, application_id: uuid.UUID) -> None:
        application = await self.get(user_id, application_id)
        await self.applications.delete(application)
        await self.session.commit()

    async def _ensure_company(self, user_id: uuid.UUID, company_id: uuid.UUID) -> None:
        if await self.companies.get(user_id, company_id) is None:
            raise NotFoundError("Company")

    async def _ensure_documents(
        self,
        user_id: uuid.UUID,
        cv_document_id: uuid.UUID | None,
        cover_letter_document_id: uuid.UUID | None,
    ) -> None:
        """RF-28: cada uno, un documento del usuario (404 si no, como la empresa) y
        del tipo que toca. La FK compuesta impone lo primero; lo segundo no puede
        comprobarlo una FK (es una columna de la otra fila)."""
        for document_id, kind in (
            (cv_document_id, DocumentKind.CV),
            (cover_letter_document_id, DocumentKind.COVER_LETTER),
        ):
            if document_id is None:
                continue
            document = await self.documents.get(user_id, document_id)
            if document is None:
                raise NotFoundError("Document")
            if document.kind != kind:
                raise AppException(
                    "Document kind does not match",
                    status_code=422,
                    code="document_kind_mismatch",
                )

    async def _raise_document_gone_or_reraise(self, error: IntegrityError) -> NoReturn:
        """Traduce la violación de las FK a documentos a 404; el resto, tal cual.

        `_ensure_documents` no basta: si otra petición borra el documento entre la
        comprobación y el flush, la FK compuesta lo rechaza. Es lo mismo que un
        documento que no existe, y sin esto el usuario vería un 500."""
        await self.session.rollback()
        if any(name in str(error.orig) for name in _DOCUMENT_FOREIGN_KEYS):
            raise NotFoundError("Document") from error
        raise error

    async def export_csv(self, user_id: uuid.UUID) -> str:
        """RF-70: todas las solicitudes del usuario, archivadas incluidas. Códigos
        en crudo (no las etiquetas de la UI) para que el fichero sea estable y, en
        el futuro, reimportable (`origin=csv_import`, evolución documentada `[C]`)."""
        applications = await self.applications.list_all(user_id)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(_CSV_HEADER)
        for application in applications:
            writer.writerow(_csv_row(application))
        return buffer.getvalue()


_CSV_HEADER = [
    "position_title",
    "company",
    "status",
    "applied_at",
    "work_mode",
    "source",
    "origin",
    "location",
    "job_url",
    "salary_min",
    "salary_max",
    "salary_currency",
    "notes",
    "job_description",
    "cv_document",
    "cover_letter_document",
    "archived_at",
    "created_at",
    "updated_at",
]


def _csv_row(application: Application) -> list[str]:
    return [
        application.position_title,
        application.company.name,
        application.status,
        _iso(application.applied_at),
        application.work_mode or "",
        application.source or "",
        application.origin,
        application.location or "",
        application.job_url or "",
        _str_or_empty(application.salary_min),
        _str_or_empty(application.salary_max),
        application.salary_currency,
        application.notes or "",
        application.job_description or "",
        _document_name(application.cv_document),
        _document_name(application.cover_letter_document),
        _iso(application.archived_at),
        _iso(application.created_at),
        _iso(application.updated_at),
    ]


def _document_name(document: Document | None) -> str:
    return document.name if document is not None else ""


def _iso(value: date | datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def _str_or_empty(value: int | None) -> str:
    return str(value) if value is not None else ""


def _today_utc() -> date:
    return datetime.now(UTC).date()


def _validate_merged(values: dict[str, Any]) -> None:
    salary_min, salary_max = values["salary_min"], values["salary_max"]
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise AppException(
            "salary_min cannot be greater than salary_max",
            status_code=422,
            code="salary_range_invalid",
        )
    if (
        values["applied_at"] is None
        and values["status"] not in STATUSES_WITHOUT_APPLIED_AT
    ):
        raise AppException(
            "applied_at is required once the application has been sent",
            status_code=422,
            code="applied_at_required",
        )
