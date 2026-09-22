import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Select, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.company import Company
from app.repositories.search import LIKE_ESCAPE, contains_pattern

CompanySort = Literal["name", "created_at", "applications_count"]


@dataclass(frozen=True)
class CompanyWithCount:
    company: Company
    applications_count: int


class CompanyRepository:
    """Acceso a `companies`. Todo método recibe user_id y filtra por él (invariante 1).

    Nunca hace commit: la transacción la confirma el service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, company: Company) -> Company:
        self.session.add(company)
        await self.session.flush()
        return company

    async def get(self, user_id: uuid.UUID, company_id: uuid.UUID) -> Company | None:
        return await self.session.scalar(
            select(Company).where(Company.user_id == user_id, Company.id == company_id)
        )

    async def get_by_name(self, user_id: uuid.UUID, name: str) -> Company | None:
        """Busca por nombre sin distinguir mayúsculas (índice único lower(name))."""
        return await self.session.scalar(
            select(Company).where(
                Company.user_id == user_id,
                func.lower(Company.name) == name.lower(),
            )
        )

    async def count(self, user_id: uuid.UUID) -> int:
        total = await self.session.scalar(
            select(func.count()).select_from(Company).where(Company.user_id == user_id)
        )
        return total or 0

    async def has_applications(self, user_id: uuid.UUID, company_id: uuid.UUID) -> bool:
        result = await self.session.scalar(
            select(
                exists().where(
                    Application.user_id == user_id,
                    Application.company_id == company_id,
                )
            )
        )
        return bool(result)

    async def count_applications(
        self, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == user_id, Application.company_id == company_id)
        )
        return total or 0

    async def list(
        self,
        user_id: uuid.UUID,
        *,
        search: str | None,
        page: int,
        limit: int,
        sort_by: CompanySort,
        descending: bool,
    ) -> tuple[list[CompanyWithCount], int]:
        applications_count = (
            select(func.count(Application.id))
            .where(
                Application.company_id == Company.id,
                Application.user_id == user_id,
            )
            .correlate(Company)
            .scalar_subquery()
            .label("applications_count")
        )

        query: Select[tuple[Company, int]] = select(Company, applications_count).where(
            Company.user_id == user_id
        )
        if search:
            query = query.where(
                Company.name.ilike(contains_pattern(search), escape=LIKE_ESCAPE)
            )

        total = await self.session.scalar(
            select(func.count()).select_from(
                query.with_only_columns(Company.id).subquery()
            )
        )

        sort_column = {
            "name": func.lower(Company.name),
            "created_at": Company.created_at,
            "applications_count": applications_count,
        }[sort_by]
        order = sort_column.desc() if descending else sort_column.asc()

        rows = await self.session.execute(
            query.order_by(order, Company.id).offset((page - 1) * limit).limit(limit)
        )
        items = [CompanyWithCount(company, count) for company, count in rows.all()]
        return items, total or 0

    async def save(self, company: Company) -> Company:
        """Envía a la BD los cambios de una empresa ya cargada (UPDATE)."""
        await self.session.flush()
        return company

    async def delete(self, company: Company) -> None:
        await self.session.delete(company)
        await self.session.flush()
