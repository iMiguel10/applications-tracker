"""Los avisos por email de F12, uno por módulo: su barrido y su compositor."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import NotificationKind
from app.services.notification_delivery_service import NotificationComposer
from app.services.notifications.interview_upcoming import (
    InterviewUpcomingComposer,
    InterviewUpcomingSweep,
)
from app.services.notifications.reminder_due import (
    ReminderDueComposer,
    ReminderDueSweep,
)

__all__ = [
    "InterviewUpcomingComposer",
    "InterviewUpcomingSweep",
    "ReminderDueComposer",
    "ReminderDueSweep",
    "composers_for",
]


def composers_for(
    session: AsyncSession,
) -> dict[NotificationKind, NotificationComposer]:
    """Un compositor por tipo de aviso. Un tipo sin compositor deja su entrega en
    `failed` sin enviar nada: añadir un aviso es añadirlo aquí."""
    return {
        NotificationKind.REMINDER_DUE: ReminderDueComposer(session),
        NotificationKind.INTERVIEW_UPCOMING: InterviewUpcomingComposer(session),
    }
