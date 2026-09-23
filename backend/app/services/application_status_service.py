import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.domain.application_status import ApplicationStatus, is_transition_allowed
from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.repositories.application_repository import ApplicationRepository
from app.repositories.application_status_change_repository import (
    ApplicationStatusChangeRepository,
)
from app.schemas.application_status_change import ApplicationStatusChangeCreate


class ApplicationStatusService:
    """Única vía para cambiar el estado de una solicitud (invariante 3).

    Bloquea la fila de la solicitud con `SELECT … FOR UPDATE` antes de decidir nada:
    dos cambios simultáneos se serializan y el segundo se valida contra el estado que
    dejó el primero, no contra el que leyó al empezar (arquitectura §8, trampa del
    `FOR UPDATE`).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.applications = ApplicationRepository(session)
        self.changes = ApplicationStatusChangeRepository(session)

    async def list_history(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> list[ApplicationStatusChange]:
        # Confirma que la solicitud existe y es del usuario antes de listar (404 si
        # no); el join de _owned() por sí solo devolvería una lista vacía, no 404.
        await self._get_owned(user_id, application_id)
        return await self.changes.list_for_application(user_id, application_id)

    async def change(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: ApplicationStatusChangeCreate,
    ) -> Application:
        application = await self._get_for_update(user_id, application_id)
        from_status = ApplicationStatus(application.status)

        if not is_transition_allowed(from_status, data.to_status):
            raise ConflictError(
                f"Cannot move from '{from_status}' to '{data.to_status}'",
                code="invalid_transition",
            )

        last_change = next(
            iter(await self.changes.recent(user_id, application_id, limit=1)), None
        )
        changed_at = (data.changed_at or datetime.now(UTC)).astimezone(UTC)
        _validate_changed_at(
            changed_at, last_change.changed_at if last_change else None
        )

        await self.changes.add(
            ApplicationStatusChange(
                application_id=application.id,
                from_status=from_status.value,
                to_status=data.to_status.value,
                changed_at=changed_at,
                note=data.note,
            )
        )

        application.status = data.to_status.value
        application.last_activity_at = datetime.now(UTC)
        # RF-33: al pasar a applied sin fecha de envío, se fija con la del cambio.
        if (
            data.to_status == ApplicationStatus.APPLIED
            and application.applied_at is None
        ):
            application.applied_at = changed_at.date()
        await self.applications.save(application)

        await self.session.commit()
        # Recarga con la empresa: la relación es lazy="raise" (ver ApplicationService).
        return await self.applications.get(user_id, application_id)  # type: ignore[return-value]

    async def undo_last(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application:
        application = await self._get_for_update(user_id, application_id)
        last_two = await self.changes.recent(user_id, application_id, limit=2)

        if len(last_two) < 2:
            raise ConflictError(
                "Cannot undo the initial status change",
                code="cannot_undo_initial_change",
            )

        last, previous = last_two
        await self.changes.delete(last)

        application.status = previous.to_status
        application.last_activity_at = datetime.now(UTC)
        await self.applications.save(application)

        await self.session.commit()
        return await self.applications.get(user_id, application_id)  # type: ignore[return-value]

    async def _get_for_update(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application:
        application = await self.applications.get_for_update(user_id, application_id)
        if application is None:
            raise NotFoundError("Application")
        return application

    async def _get_owned(self, user_id: uuid.UUID, application_id: uuid.UUID) -> None:
        if await self.applications.get(user_id, application_id) is None:
            raise NotFoundError("Application")


def _validate_changed_at(
    changed_at: datetime, last_changed_at: datetime | None
) -> None:
    """RF-30 y arquitectura §8, paso 4: `changed_at` entre el último cambio y ahora,
    para que el historial no cuente algo que aún no ha pasado o que pasó antes de lo
    que ya se había registrado."""
    now = datetime.now(UTC)
    if changed_at > now:
        raise AppException(
            "changed_at cannot be in the future",
            status_code=422,
            code="changed_at_in_future",
        )
    if last_changed_at is not None and changed_at < last_changed_at:
        raise AppException(
            "changed_at cannot be earlier than the last change",
            status_code=422,
            code="changed_at_before_last_change",
        )
