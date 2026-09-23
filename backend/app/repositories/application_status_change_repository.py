import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange


class ApplicationStatusChangeRepository:
    """Acceso a `application_status_changes`. Es una tabla hija (vía `application_id`):
    se filtra haciendo join con `applications` para exigir también `user_id`
    (arquitectura §7), igual que si tuviera su propia columna de usuario.

    Nunca hace commit ni borra salvo `delete`, que solo usa deshacer.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, change: ApplicationStatusChange) -> ApplicationStatusChange:
        self.session.add(change)
        await self.session.flush()
        return change

    async def list_for_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> list[ApplicationStatusChange]:
        """Todo el historial, del más reciente al más antiguo (orden por `seq`, 0004)."""
        result = await self.session.scalars(
            self._owned(user_id, application_id).order_by(
                ApplicationStatusChange.seq.desc()
            )
        )
        return list(result.all())

    async def recent(
        self, user_id: uuid.UUID, application_id: uuid.UUID, limit: int
    ) -> Sequence[ApplicationStatusChange]:
        """Los `limit` cambios más recientes, del más reciente al más antiguo."""
        result = await self.session.scalars(
            self._owned(user_id, application_id)
            .order_by(ApplicationStatusChange.seq.desc())
            .limit(limit)
        )
        return result.all()

    async def delete(self, change: ApplicationStatusChange) -> None:
        await self.session.delete(change)
        await self.session.flush()

    def _owned(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Select[tuple[ApplicationStatusChange]]:
        return (
            select(ApplicationStatusChange)
            .join(Application, Application.id == ApplicationStatusChange.application_id)
            .where(
                Application.user_id == user_id,
                ApplicationStatusChange.application_id == application_id,
            )
        )
