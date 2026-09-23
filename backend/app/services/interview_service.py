import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.application import Application
from app.models.interview import Interview
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_repository import InterviewRepository
from app.schemas.interview import InterviewCreate, InterviewUpdate


class InterviewService:
    """Reglas de negocio de las entrevistas (RF-40…42). Dueño de la transacción.

    El estado de la solicitud NO cambia aquí (invariante 3): programar una
    entrevista solo actualiza `last_activity_at`. Sugerir el paso a `interviewing`
    es cosa del frontend, con los `allowed_transitions` que ya expone la solicitud.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.interviews = InterviewRepository(session)
        self.applications = ApplicationRepository(session)

    async def list(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> list[Interview]:
        await self._ensure_application(user_id, application_id)
        return await self.interviews.list_for_application(user_id, application_id)

    async def create(
        self, user_id: uuid.UUID, application_id: uuid.UUID, data: InterviewCreate
    ) -> Interview:
        application = await self._ensure_application(user_id, application_id)
        interview = Interview(application_id=application_id, **data.model_dump())
        await self.interviews.add(interview)
        await self._touch(application)
        await self.session.commit()
        return interview

    async def update(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        interview_id: uuid.UUID,
        data: InterviewUpdate,
    ) -> Interview:
        application = await self._ensure_application(user_id, application_id)
        interview = await self._get_or_404(user_id, application_id, interview_id)

        changes: dict[str, Any] = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(interview, field, value)
        await self.interviews.save(interview)
        await self._touch(application)
        await self.session.commit()
        return interview

    async def delete(
        self, user_id: uuid.UUID, application_id: uuid.UUID, interview_id: uuid.UUID
    ) -> None:
        application = await self._ensure_application(user_id, application_id)
        interview = await self._get_or_404(user_id, application_id, interview_id)
        await self.interviews.delete(interview)
        await self._touch(application)
        await self.session.commit()

    async def _ensure_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application:
        application = await self.applications.get(user_id, application_id)
        if application is None:
            raise NotFoundError("Application")
        return application

    async def _get_or_404(
        self, user_id: uuid.UUID, application_id: uuid.UUID, interview_id: uuid.UUID
    ) -> Interview:
        interview = await self.interviews.get(user_id, application_id, interview_id)
        if interview is None:
            raise NotFoundError("Interview")
        return interview

    async def _touch(self, application: Application) -> None:
        """RF-64 / arquitectura §5: tocar entrevistas cuenta como actividad."""
        application.last_activity_at = datetime.now(UTC)
        await self.applications.save(application)
