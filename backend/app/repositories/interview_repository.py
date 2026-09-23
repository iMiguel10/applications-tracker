import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interview import InterviewOutcome
from app.models.application import Application
from app.models.company import Company
from app.models.interview import Interview


class InterviewRepository:
    """Acceso a `interviews`. Es una tabla hija (vía `application_id`): se filtra
    haciendo join con `applications` para exigir también `user_id` (arquitectura §7).

    Nunca hace commit: la transacción la confirma el service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, interview: Interview) -> Interview:
        self.session.add(interview)
        await self.session.flush()
        return interview

    async def get(
        self, user_id: uuid.UUID, application_id: uuid.UUID, interview_id: uuid.UUID
    ) -> Interview | None:
        return await self.session.scalar(
            select(Interview)
            .join(Application, Application.id == Interview.application_id)
            .where(
                Application.user_id == user_id,
                Interview.application_id == application_id,
                Interview.id == interview_id,
            )
        )

    async def list_for_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> list[Interview]:
        result = await self.session.scalars(
            select(Interview)
            .join(Application, Application.id == Interview.application_id)
            .where(
                Application.user_id == user_id,
                Interview.application_id == application_id,
            )
            .order_by(Interview.scheduled_at)
        )
        return list(result.all())

    async def list_upcoming(
        self, user_id: uuid.UUID, *, after: datetime, limit: int
    ) -> Sequence[Row[tuple[Interview, Application, Company]]]:
        """RF-63: próximas entrevistas del usuario (cualquier solicitud), con la
        solicitud y la empresa para mostrarlas sin una consulta por fila.

        Sin relación declarada `Interview.application` (no hace falta fuera de
        aquí): se hace explícito con un `select` de las tres tablas.
        """
        result = await self.session.execute(
            self._upcoming(user_id, after=after)
            .order_by(Interview.scheduled_at.asc())
            .limit(limit)
        )
        return result.all()

    async def count_upcoming(self, user_id: uuid.UUID, *, after: datetime) -> int:
        """Total de próximas entrevistas, sin el límite de `list_upcoming` (para el
        "N más" del widget del dashboard)."""
        total = await self.session.scalar(
            select(func.count()).select_from(
                self._upcoming(user_id, after=after)
                .with_only_columns(Interview.id)
                .subquery()
            )
        )
        return total or 0

    def _upcoming(
        self, user_id: uuid.UUID, *, after: datetime
    ) -> Select[tuple[Interview, Application, Company]]:
        return (
            select(Interview, Application, Company)
            .join(Application, Application.id == Interview.application_id)
            .join(Company, Company.id == Application.company_id)
            .where(
                Application.user_id == user_id,
                Interview.scheduled_at >= after,
                Interview.outcome == InterviewOutcome.PENDING.value,
            )
        )

    async def save(self, interview: Interview) -> Interview:
        await self.session.flush()
        return interview

    async def delete(self, interview: Interview) -> None:
        await self.session.delete(interview)
        await self.session.flush()
