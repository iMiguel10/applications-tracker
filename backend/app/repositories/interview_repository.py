import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
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

    async def save(self, interview: Interview) -> Interview:
        await self.session.flush()
        return interview

    async def delete(self, interview: Interview) -> None:
        await self.session.delete(interview)
        await self.session.flush()
