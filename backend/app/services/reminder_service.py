import uuid
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, LimitReachedError, NotFoundError
from app.domain.reminder import MAX_PENDING_REMINDERS_PER_USER, ReminderStatus
from app.models.reminder import Reminder
from app.repositories.application_repository import ApplicationRepository
from app.repositories.reminder_repository import (
    ReminderFilters,
    ReminderRepository,
    ReminderSort,
)
from app.schemas.reminder import ReminderCreate, ReminderListQuery
from app.services.notifications.base import NotificationChannel
from app.services.notifications.in_app import InAppChannel


class ReminderService:
    """Reglas de negocio de los recordatorios (RF-50…53). Dueño de la transacción."""

    def __init__(
        self, session: AsyncSession, channel: NotificationChannel | None = None
    ) -> None:
        self.session = session
        self.reminders = ReminderRepository(session)
        self.applications = ApplicationRepository(session)
        # Costura de RF-53: el service solo conoce la interfaz. En el MVP siempre es
        # InAppChannel; un canal nuevo se inyecta aquí, no cambia el resto del service.
        self.channel = channel or InAppChannel()

    async def list(
        self, user_id: uuid.UUID, query: ReminderListQuery
    ) -> tuple[list[Reminder], int]:
        filters = ReminderFilters(
            application_id=query.application_id,
            statuses=query.statuses,
            due_before=query.due_before,
            due_after=query.due_after,
        )
        return await self.reminders.list(
            user_id,
            filters,
            page=query.page,
            limit=query.limit,
            sort_by=cast(ReminderSort, query.sort_by),
            descending=query.order == "desc",
        )

    async def create(self, user_id: uuid.UUID, data: ReminderCreate) -> Reminder:
        if (
            await self.reminders.count_pending(user_id)
            >= MAX_PENDING_REMINDERS_PER_USER
        ):
            raise LimitReachedError("reminders", MAX_PENDING_REMINDERS_PER_USER)
        if data.application_id is not None:
            await self._ensure_application(user_id, data.application_id)

        reminder = Reminder(user_id=user_id, **data.model_dump())
        await self.reminders.add(reminder)
        await self.channel.send(reminder)
        await self.session.commit()
        return await self._get_or_404(user_id, reminder.id)

    async def complete(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> Reminder:
        reminder = await self._get_or_404(user_id, reminder_id)
        self._ensure_pending(reminder)
        reminder.status = ReminderStatus.DONE.value
        reminder.completed_at = datetime.now(UTC)
        await self.reminders.save(reminder)
        await self.session.commit()
        return reminder

    async def dismiss(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> Reminder:
        reminder = await self._get_or_404(user_id, reminder_id)
        self._ensure_pending(reminder)
        reminder.status = ReminderStatus.DISMISSED.value
        await self.reminders.save(reminder)
        await self.session.commit()
        return reminder

    async def _get_or_404(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> Reminder:
        reminder = await self.reminders.get(user_id, reminder_id)
        if reminder is None:
            raise NotFoundError("Reminder")
        return reminder

    async def _ensure_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> None:
        if await self.applications.get(user_id, application_id) is None:
            raise NotFoundError("Application")

    def _ensure_pending(self, reminder: Reminder) -> None:
        # Idempotencia a medias a propósito: completar un recordatorio ya descartado
        # (o viceversa) sería confuso, así que se rechaza en vez de sobrescribir.
        if reminder.status != ReminderStatus.PENDING.value:
            raise ConflictError(
                "Only a pending reminder can change status this way",
                code="reminder_not_pending",
            )
