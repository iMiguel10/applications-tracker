"""Resumen semanal (RF-82): el barrido que lo reclama el lunes por la mañana en la
zona de cada usuario y el compositor que lo escribe con lo del dashboard."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.dashboard import WAITING_STATUSES
from app.domain.dates import format_local_date, format_local_datetime
from app.domain.notifications import (
    DIGEST_LIST_LIMIT,
    NotificationKind,
    digest_key_if_due,
)
from app.domain.reminder import ReminderStatus
from app.domain.user import email_language
from app.infra.email.templates import EmailTemplates, RenderedEmail
from app.infra.queue import JobQueue
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.identity_repository import IdentityRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.repositories.reminder_repository import ReminderFilters, ReminderRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_delivery_service import SingleDeliveryComposer
from app.services.notifications.sweep import ClaimingSweep, Cursor, SweepCandidate

KIND = NotificationKind.WEEKLY_DIGEST
_WAITING = [status.value for status in WAITING_STATUSES]
# En el orden del ciclo de vida, para la línea "en curso" del resumen.
_WAITING_ORDER = ["applied", "screening", "interviewing", "offer"]


class WeeklyDigestSweep:
    """Barrido de RF-82, cada hora: reclama el resumen de los usuarios para los que,
    en su zona horaria, ya es lunes a partir de las 8:00. La consulta no puede
    decidirlo (la hora local se calcula en Python), así que la página de candidatos
    se filtra aquí y se descartan los que ya tienen el resumen de esta semana."""

    def __init__(
        self,
        session: AsyncSession,
        job_queue: JobQueue,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.users = UserRepository(session)
        self.deliveries = NotificationDeliveryRepository(session)
        self.sweep = ClaimingSweep(session, job_queue, identities)

    async def run(self, now: datetime) -> int:
        async def fetch_page(after: Cursor | None, limit: int) -> list[SweepCandidate]:
            # Se sigue leyendo hasta encontrar candidatos o agotar los usuarios: una
            # página vacía tras el filtro no significa que no queden.
            while True:
                rows = await self.users.list_for_digest(after=after, limit=limit)
                if not rows:
                    return []
                after = (rows[-1].created_at, rows[-1].user_id)
                due = [
                    (row, key)
                    for row in rows
                    if (key := digest_key_if_due(now, row.timezone)) is not None
                ]
                blocked = await self.deliveries.blocking_keys(
                    KIND, [(row.user_id, key) for row, key in due], now
                )
                candidates = [
                    SweepCandidate(
                        user_id=row.user_id,
                        supertokens_user_id=row.supertokens_user_id,
                        dedupe_key=key,
                        # La posición de la página leída, no del último candidato:
                        # así la siguiente no vuelve a leer lo ya filtrado.
                        cursor=after,
                    )
                    for row, key in due
                    if (row.user_id, key) not in blocked
                ]
                if candidates:
                    return candidates

        return await self.sweep.claim_all(KIND, fetch_page, now)


class WeeklyDigestComposer(SingleDeliveryComposer):
    """Escribe el resumen con lo mismo que el dashboard, a la hora del reclamo:
    entrevistas de los próximos 7 días, recordatorios vencidos y de la semana,
    solicitudes sin actividad y cuántas hay en curso. Sale también sin nada
    pendiente: quien lo activó espera recibirlo cada lunes. None solo si el usuario
    desactivó el aviso entre el barrido y el envío."""

    def __init__(
        self,
        session: AsyncSession,
        templates: EmailTemplates | None = None,
        website_domain: str = settings.website_domain,
    ) -> None:
        self.applications = ApplicationRepository(session)
        self.interviews = InterviewRepository(session)
        self.reminders = ReminderRepository(session)
        self.templates = templates or EmailTemplates()
        self.website = website_domain.rstrip("/")

    async def compose_one(
        self, delivery: NotificationDelivery, user: User, unsubscribe_link: str
    ) -> RenderedEmail | None:
        if not user.notify_weekly_digest:
            return None
        now = delivery.claimed_at
        week_end = now + timedelta(days=7)
        language = email_language(user.language)

        def when(instant: datetime) -> str:
            return format_local_datetime(instant, user.timezone, language)

        interviews = [
            {
                "when": when(interview.scheduled_at),
                "position": application.position_title,
                "company": company.name,
                "interview_type": interview.interview_type,
                "link": f"{self.website}/applications/{application.id}",
            }
            for interview, application, company in await self.interviews.list_upcoming(
                user.id, after=now, limit=DIGEST_LIST_LIMIT
            )
            if interview.scheduled_at < week_end
        ]

        reminders, reminders_total = await self.reminders.list(
            user.id,
            ReminderFilters(statuses=[ReminderStatus.PENDING], due_before=week_end),
            page=1,
            limit=DIGEST_LIST_LIMIT,
            sort_by="due_at",
            descending=False,
        )
        reminder_items: list[dict[str, Any]] = [
            {
                "title": reminder.title,
                "when": when(reminder.due_at),
                "overdue": reminder.due_at <= now,
            }
            for reminder in reminders
        ]

        stale, stale_total = await self.applications.list_stale(
            user.id,
            statuses=_WAITING,
            before=now - timedelta(days=user.stale_after_days),
            limit=DIGEST_LIST_LIMIT,
        )
        stale_items = [
            {
                "position": application.position_title,
                "company": application.company.name,
                "days": (now - application.last_activity_at).days,
                "link": f"{self.website}/applications/{application.id}",
            }
            for application in stale
        ]

        counts: dict[str, int] = {
            status: count
            for status, count in await self.applications.count_by_status(user.id)
        }
        in_progress = [
            {"status": status, "count": counts[status]}
            for status in _WAITING_ORDER
            if counts.get(status)
        ]

        return self.templates.render(
            KIND.value,
            language,
            {
                "week_of": format_local_date(now, user.timezone, language),
                "interviews": interviews,
                "reminders": reminder_items,
                "reminders_more": reminders_total - len(reminder_items),
                "stale": stale_items,
                "stale_more": stale_total - len(stale_items),
                "stale_after_days": user.stale_after_days,
                "in_progress": in_progress,
                "dashboard_link": f"{self.website}/dashboard",
                "reminders_link": f"{self.website}/reminders",
                "preferences_link": f"{self.website}/preferences",
                "unsubscribe_link": unsubscribe_link,
            },
        )
