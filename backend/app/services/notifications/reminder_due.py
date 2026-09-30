"""Aviso de recordatorio vencido (RF-80): el barrido que lo reclama y el
compositor que escribe el email."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.dates import format_local_datetime
from app.domain.notifications import (
    REMINDER_DUE_WINDOW,
    SWEEP_MAX_CLAIMS,
    NotificationKind,
    reminder_due_key,
    reminder_id_from_key,
)
from app.domain.reminder import ReminderStatus
from app.domain.user import DEFAULT_LANGUAGE, Language
from app.infra.email.templates import EmailTemplates, RenderedEmail
from app.infra.queue import JobQueue
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.reminder_repository import ReminderRepository
from app.services.notification_delivery_service import NotificationDeliveryService

logger = logging.getLogger(__name__)

KIND = NotificationKind.REMINDER_DUE
# Candidatos que se leen por consulta; se sigue leyendo hasta agotarlos o hasta
# SWEEP_MAX_CLAIMS reclamos, para que las cuentas sin verificar (que no reclaman)
# no puedan ocupar la pasada entera.
_PAGE_SIZE = 200


def email_language(user: User) -> Language:
    """RF-86: el idioma de la cuenta, o el de por defecto si sigue al navegador (un
    barrido no tiene navegador al que preguntar)."""
    return Language(user.language) if user.language else DEFAULT_LANGUAGE


class ReminderDueSweep:
    """Barrido de RF-80, cada minuto: reclama un aviso por recordatorio vencido en
    las últimas 24 h y encola su envío. Solo cuentas con el aviso activado (lo
    filtra la consulta) y el email verificado (lo dice SuperTokens): una cuenta sin
    verificar no genera ni reclamos, así que al verificarla no recibe de golpe lo
    acumulado (segundo plano §3)."""

    def __init__(
        self,
        session: AsyncSession,
        job_queue: JobQueue,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.reminders = ReminderRepository(session)
        self.deliveries = NotificationDeliveryService(session)
        self.job_queue = job_queue
        self.identities = identities or IdentityRepository()

    async def run(self, now: datetime) -> int:
        verified: dict[str, bool] = {}
        claimed = 0
        after = None
        while claimed < SWEEP_MAX_CLAIMS:
            candidates = await self.reminders.list_due_for_notification(
                notify_after=now - REMINDER_DUE_WINDOW,
                now=now,
                after=after,
                limit=_PAGE_SIZE,
            )
            if not candidates:
                break
            for candidate in candidates:
                account = candidate.supertokens_user_id
                if account not in verified:
                    verified[account] = await self.identities.is_email_verified(account)
                if not verified[account]:
                    continue
                delivery_id = await self.deliveries.claim(
                    candidate.user_id,
                    KIND,
                    reminder_due_key(candidate.reminder_id),
                    now,
                )
                if delivery_id is None:
                    continue
                await self.deliveries.enqueue_send(
                    self.job_queue, delivery_id, candidate.user_id
                )
                claimed += 1
                if claimed >= SWEEP_MAX_CLAIMS:
                    break
            last = candidates[-1]
            after = (last.due_at, last.reminder_id)
        if claimed:
            logger.info("%d avisos de recordatorio vencido reclamados", claimed)
        return claimed


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

        language = email_language(user)
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
