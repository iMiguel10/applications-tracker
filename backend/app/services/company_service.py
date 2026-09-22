import uuid
from typing import NoReturn, cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppException,
    ConflictError,
    LimitReachedError,
    NotFoundError,
)
from app.domain.application import MAX_COMPANIES_PER_USER
from app.models.company import Company
from app.repositories.company_repository import (
    CompanyRepository,
    CompanySort,
    CompanyWithCount,
)
from app.schemas.company import CompanyCreate, CompanyListQuery, CompanyUpdate

NAME_UNIQUE_INDEX = "uq_companies_user_id_lower_name"


class CompanyService:
    """Reglas de negocio de las empresas. Dueño de la transacción: es quien hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.companies = CompanyRepository(session)

    async def list(
        self, user_id: uuid.UUID, query: CompanyListQuery
    ) -> tuple[list[CompanyWithCount], int]:
        return await self.companies.list(
            user_id,
            search=query.q,
            page=query.page,
            limit=query.limit,
            sort_by=cast(CompanySort, query.sort_by),
            descending=query.order == "desc",
        )

    async def get(self, user_id: uuid.UUID, company_id: uuid.UUID) -> CompanyWithCount:
        company = await self._get_or_404(user_id, company_id)
        count = await self.companies.count_applications(user_id, company_id)
        return CompanyWithCount(company, count)

    async def create(self, user_id: uuid.UUID, data: CompanyCreate) -> CompanyWithCount:
        if await self.companies.count(user_id) >= MAX_COMPANIES_PER_USER:
            raise LimitReachedError("companies", MAX_COMPANIES_PER_USER)
        await self._ensure_name_available(user_id, data.name)

        company = Company(user_id=user_id, **data.model_dump())
        try:
            await self.companies.add(company)
        except IntegrityError as error:
            await self._raise_name_taken_or_reraise(error)
        await self.session.commit()
        return CompanyWithCount(company, 0)

    async def update(
        self, user_id: uuid.UUID, company_id: uuid.UUID, data: CompanyUpdate
    ) -> CompanyWithCount:
        company = await self._get_or_404(user_id, company_id)
        # Solo los campos enviados: distinguir "no enviado" de null (vaciar).
        changes = data.model_dump(exclude_unset=True)

        if "name" in changes:
            if changes["name"] is None:
                raise AppException(
                    "Company name cannot be empty",
                    status_code=422,
                    code="name_required",
                )
            if changes["name"].lower() != company.name.lower():
                await self._ensure_name_available(user_id, changes["name"])

        for field, value in changes.items():
            setattr(company, field, value)
        try:
            await self.companies.save(company)
        except IntegrityError as error:
            await self._raise_name_taken_or_reraise(error)
        await self.session.commit()

        count = await self.companies.count_applications(user_id, company_id)
        return CompanyWithCount(company, count)

    async def delete(self, user_id: uuid.UUID, company_id: uuid.UUID) -> None:
        company = await self._get_or_404(user_id, company_id)
        # RF-12. La FK (RESTRICT) lo impediría igualmente, pero con un 500.
        if await self.companies.has_applications(user_id, company_id):
            raise ConflictError(
                "Company has applications and cannot be deleted", code="company_in_use"
            )
        await self.companies.delete(company)
        await self.session.commit()

    async def _get_or_404(self, user_id: uuid.UUID, company_id: uuid.UUID) -> Company:
        company = await self.companies.get(user_id, company_id)
        if company is None:
            raise NotFoundError("Company")
        return company

    async def _ensure_name_available(self, user_id: uuid.UUID, name: str) -> None:
        if await self.companies.get_by_name(user_id, name) is not None:
            raise ConflictError(
                "A company with that name already exists", code="company_name_taken"
            )

    async def _raise_name_taken_or_reraise(self, error: IntegrityError) -> NoReturn:
        """Traduce la violación del índice de nombre único a 409; el resto, tal cual.

        La comprobación previa (_ensure_name_available) no basta: dos peticiones
        simultáneas con el mismo nombre la pasan las dos, y la segunda choca con el
        índice al hacer flush. Sin esto, el usuario vería un 500.
        """
        await self.session.rollback()
        if NAME_UNIQUE_INDEX in str(error.orig):
            raise ConflictError(
                "A company with that name already exists", code="company_name_taken"
            ) from error
        raise error
