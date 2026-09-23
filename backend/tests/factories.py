"""Creación rápida de datos de prueba, directamente con los repositories.

Cada test prepara lo que necesita en una línea y sin pasar por la API, para que un
fallo apunte a lo que se prueba y no a la preparación.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.models.company import Company
from app.models.interview import Interview
from app.models.reminder import Reminder
from app.repositories.application_repository import ApplicationRepository
from app.repositories.application_status_change_repository import (
    ApplicationStatusChangeRepository,
)
from app.repositories.company_repository import CompanyRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.reminder_repository import ReminderRepository


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
    """Crea una solicitud con su cambio inicial de historial (from_status NULL),
    igual que ApplicationService.create (invariante 4)."""
    company = company or await make_company(session, user_id)
    values: dict[str, Any] = {
        "position_title": "Backend Developer",
        "status": "applied",
        "applied_at": date(2026, 9, 1),
    } | fields
    application = await ApplicationRepository(session).add(
        Application(user_id=user_id, company_id=company.id, **values)
    )
    await make_status_change(
        session, application, from_status=None, to_status=values["status"]
    )
    return application


async def make_status_change(
    session: AsyncSession,
    application: Application,
    to_status: str,
    from_status: str | None = "",
    changed_at: datetime | None = None,
    note: str | None = None,
) -> ApplicationStatusChange:
    """Añade un cambio al historial de `application` sin pasar por
    ApplicationStatusService (para preparar un historial concreto en el test).

    `from_status=""` (el valor por defecto, distinto de None) toma el estado
    actual de `application` como origen; pásalo explícitamente a None para el
    cambio inicial.
    """
    return await ApplicationStatusChangeRepository(session).add(
        ApplicationStatusChange(
            application_id=application.id,
            from_status=application.status if from_status == "" else from_status,
            to_status=to_status,
            changed_at=changed_at or datetime.now(UTC),
            note=note,
        )
    )


async def make_interview(
    session: AsyncSession, application: Application, **fields: Any
) -> Interview:
    values: dict[str, Any] = {
        "scheduled_at": datetime.now(UTC) + timedelta(days=3),
    } | fields
    return await InterviewRepository(session).add(
        Interview(application_id=application.id, **values)
    )


async def make_reminder(
    session: AsyncSession, user_id: uuid.UUID, **fields: Any
) -> Reminder:
    values: dict[str, Any] = {
        "title": "Hacer seguimiento",
        "due_at": datetime.now(UTC) + timedelta(days=1),
    } | fields
    return await ReminderRepository(session).add(Reminder(user_id=user_id, **values))
