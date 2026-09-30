"""Aviso de recordatorio vencido (RF-80): el barrido que lo reclama y el
compositor que escribe el email."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.dates import format_local_datetime
from app.domain.notifications import (
    REMINDER_DUE_WINDOW,
    NotificationKind,
    reminder_due_key,
    reminder_id_from_key,
)
from app.domain.reminder import ReminderStatus
from app.domain.user import email_language
from app.infra.email.templates import EmailTemplates, RenderedEmail
from app.infra.queue import JobQueue
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.reminder_repository import ReminderRepository
from app.services.notifications.sweep import ClaimingSweep, Cursor, SweepCandidate

logger = logging.getLogger(__name__)

KIND = NotificationKind.REMINDER_DUE


class ReminderDueSweep:
    """Barrido de RF-80, cada minuto: un aviso por recordatorio pendiente cuyo
    momento de aviso (la fecha menos la antelación) cayó en las últimas 24 h."""

    def __init__(
        self,
        session: AsyncSession,
        job_queue: JobQueue,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.reminders = ReminderRepository(session)
        self.sweep = ClaimingSweep(session, job_queue, identities)

    async def run(self, now: datetime) -> int:
        async def fetch_page(after: Cursor | None, limit: int) -> list[SweepCandidate]:
            due = await self.reminders.list_due_for_notification(
                notify_after=now - REMINDER_DUE_WINDOW,
                now=now,
                after=after,
                limit=limit,
            )
            return [
                SweepCandidate(
                    user_id=row.user_id,
                    supertokens_user_id=row.supertokens_user_id,
                    dedupe_key=reminder_due_key(row.reminder_id),
                    cursor=(row.due_at, row.reminder_id),
                )
                for row in due
            ]

        return await self.sweep.claim_all(KIND, fetch_page, now)


class ReminderDueComposer:
    """Escribe el email de un recordatorio vencido. None si ya no hay nada que
    avisar: el recordatorio se completó, se descartó o se borró, o el usuario
    desactivó el aviso, entre el barrido y el envío."""

    def __init__(
        self,
        session: AsyncSession,
        templates: EmailTemplates | None = None,
        website_domain: str = settings.website_domain,
    ) -> None:
        self.reminders = ReminderRepository(session)
        self.templates = templates or EmailTemplates()
        self.website = website_domain.rstrip("/")

    async def compose(
        self, delivery: NotificationDelivery, user: User, unsubscribe_link: str
    ) -> RenderedEmail | None:
        reminder_id = reminder_id_from_key(delivery.dedupe_key)
        if reminder_id is None or not user.notify_reminder_due:
            return None
        reminder = await self.reminders.get_for_notification(user.id, reminder_id)
        if reminder is None or reminder.status != ReminderStatus.PENDING:
            return None

        language = email_language(user.language)
        application = reminder.application
        return self.templates.render(
            KIND.value,
            language,
            {
                # El título lo escribe el usuario y va en el asunto: un salto de
                # línea en una cabecera haría que el SMTP lo rechazara.
                "title": " ".join(reminder.title.split()),
                "due": format_local_datetime(reminder.due_at, user.timezone, language),
                # Con antelación, el aviso sale antes de la fecha: "vence", no "venció".
                # Se compara con el reclamo, que es cuando el barrido decidió avisar.
                "upcoming": reminder.due_at > delivery.claimed_at,
                "application": (
                    f"{application.position_title} · {application.company.name}"
                    if application is not None
                    else None
                ),
                "link": (
                    f"{self.website}/applications/{application.id}"
                    if application is not None
                    else f"{self.website}/reminders"
                ),
                "preferences_link": f"{self.website}/preferences",
                "unsubscribe_link": unsubscribe_link,
            },
        )
