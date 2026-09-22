"""Creación rápida de datos de prueba, directamente con los repositories.

Cada test prepara lo que necesita en una línea y sin pasar por la API, para que un
fallo apunte a lo que se prueba y no a la preparación.
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.company import Company
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository


async def make_company(
    session: AsyncSession, user_id: uuid.UUID, name: str | None = None, **fields: Any
) -> Company:
    return await CompanyRepository(session).add(
        Company(
            user_id=user_id, name=name or f"Company {uuid.uuid4().hex[:8]}", **fields
        )
    )


async def make_application(
    session: AsyncSession,
    user_id: uuid.UUID,
    company: Company | None = None,
    **fields: Any,
) -> Application:
    company = company or await make_company(session, user_id)
    values: dict[str, Any] = {
        "position_title": "Backend Developer",
        "status": "applied",
        "applied_at": date(2026, 9, 1),
    } | fields
    return await ApplicationRepository(session).add(
        Application(user_id=user_id, company_id=company.id, **values)
    )
