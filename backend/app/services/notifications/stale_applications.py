"""Aviso de solicitudes sin actividad (RF-83): el barrido que lo reclama y el
compositor que escribe el email con la lista."""

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.dashboard import WAITING_STATUSES
from app.domain.dates import format_local_date
from app.domain.notifications import NotificationKind, stale_from_key, stale_key
from app.domain.user import email_language
from app.infra.email.templates import EmailTemplates
from app.infra.queue import JobQueue
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.identity_repository import IdentityRepository
from app.services.notification_delivery_service import Composition
from app.services.notifications.sweep import ClaimingSweep, Cursor, SweepCandidate

KIND = NotificationKind.STALE_APPLICATION
_WAITING = sorted(status.value for status in WAITING_STATUSES)


class StaleApplicationSweep:
    """Barrido de RF-83, cada hora: un aviso por solicitud y periodo de
    inactividad, agrupados en **un solo email por usuario y pasada**. El primer
    barrido encuentra todas las solicitudes paradas de golpe: sin agrupar, sería un
    email por cada una (segundo plano §3)."""

    def __init__(
        self,
        session: AsyncSession,
        job_queue: JobQueue,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.applications = ApplicationRepository(session)
        self.sweep = ClaimingSweep(session, job_queue, identities)

    async def run(self, now: datetime) -> int:
        async def fetch_page(after: Cursor | None, limit: int) -> list[SweepCandidate]:
            stale = await self.applications.list_stale_for_notification(
                statuses=_WAITING, now=now, after=after, limit=limit
            )
            return [
                SweepCandidate(
                    user_id=row.user_id,
                    supertokens_user_id=row.supertokens_user_id,
                    dedupe_key=stale_key(row.application_id, row.last_activity_at),
                    cursor=(row.last_activity_at, row.application_id),
                )
                for row in stale
            ]

        return await self.sweep.claim_all(KIND, fetch_page, now, group_per_user=True)


class StaleApplicationsComposer:
    """Escribe el email con la lista de solicitudes sin actividad. Solo cubre las
    que siguen paradas al enviarlo: una que se movió, se archivó, cambió a un estado
    final o dejó de pasar el umbral entre el barrido y el envío sale de la lista (y
    su entrega se borra). None si no queda ninguna o el usuario desactivó el aviso.
    """

    def __init__(
        self,
        session: AsyncSession,
        templates: EmailTemplates | None = None,
        website_domain: str = settings.website_domain,
    ) -> None:
        self.applications = ApplicationRepository(session)
        self.templates = templates or EmailTemplates()
        self.website = website_domain.rstrip("/")

    async def compose(
        self,
        deliveries: Sequence[NotificationDelivery],
        user: User,
        unsubscribe_link: str,
    ) -> Composition | None:
        if not user.notify_stale:
            return None
        keys = {
            delivery.id: parsed
            for delivery in deliveries
            if (parsed := stale_from_key(delivery.dedupe_key)) is not None
        }
        applications = {
            application.id: application
            for application in await self.applications.get_many_for_notification(
                user.id, [application_id for application_id, _ in keys.values()]
            )
        }
        threshold = timedelta(days=user.stale_after_days)

        covered: list[NotificationDelivery] = []
        items = []
        for delivery in deliveries:
            if delivery.id not in keys:
                continue
            application_id, seconds = keys[delivery.id]
            application = applications.get(application_id)
            if (
                application is None
                or application.archived_at is not None
                or application.status not in _WAITING
                or int(application.last_activity_at.timestamp()) != seconds
                or delivery.claimed_at - application.last_activity_at <= threshold
            ):
                continue
            covered.append(delivery)
            items.append(application)
        if not covered:
            return None

        language = email_language(user.language)
        items.sort(key=lambda application: application.last_activity_at)
        email = self.templates.render(
            KIND.value,
            language,
            {
                "applications": [
                    {
                        # Texto del usuario en el asunto: una sola línea.
                        "position": " ".join(application.position_title.split()),
                        "company": " ".join(application.company.name.split()),
                        "status": application.status,
                        "since": format_local_date(
                            application.last_activity_at, user.timezone, language
                        ),
                        "days": (
                            covered[0].claimed_at - application.last_activity_at
                        ).days,
                        "link": f"{self.website}/applications/{application.id}",
                    }
                    for application in items
                ],
                "dashboard_link": f"{self.website}/dashboard",
                "preferences_link": f"{self.website}/preferences",
                "unsubscribe_link": unsubscribe_link,
            },
        )
        return Composition(email, covered)
