"""Aviso de entrevista próxima (RF-81): el barrido que lo reclama y el compositor
que escribe el email."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.dates import format_local_datetime
from app.domain.interview import InterviewOutcome
from app.domain.notifications import (
    NotificationKind,
    interview_from_key,
    interview_key,
)
from app.domain.user import email_language
from app.infra.email.templates import EmailTemplates, RenderedEmail
from app.infra.queue import JobQueue
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.interview_repository import InterviewRepository
from app.services.notifications.sweep import ClaimingSweep, Cursor, SweepCandidate

KIND = NotificationKind.INTERVIEW_UPCOMING


class InterviewUpcomingSweep:
    """Barrido de RF-81, cada 5 minutos: un aviso por entrevista pendiente que aún
    no ha empezado y cuyo momento de aviso (la hora menos la antelación de la
    cuenta) ya llegó. La clave lleva la hora: moverla es un aviso nuevo."""

    def __init__(
        self,
        session: AsyncSession,
        job_queue: JobQueue,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.interviews = InterviewRepository(session)
        self.sweep = ClaimingSweep(session, job_queue, identities)

    async def run(self, now: datetime) -> int:
        async def fetch_page(after: Cursor | None, limit: int) -> list[SweepCandidate]:
            upcoming = await self.interviews.list_upcoming_for_notification(
                now=now, after=after, limit=limit
            )
            return [
                SweepCandidate(
                    user_id=row.user_id,
                    supertokens_user_id=row.supertokens_user_id,
                    dedupe_key=interview_key(row.interview_id, row.scheduled_at),
                    cursor=(row.scheduled_at, row.interview_id),
                )
                for row in upcoming
            ]

        return await self.sweep.claim_all(KIND, fetch_page, now)


class InterviewUpcomingComposer:
    """Escribe el email de una entrevista próxima. None si ya no hay nada que
    avisar: la entrevista se borró, se movió (su aviso es otro motivo, que ya
    reclamará el barrido), tiene resultado, o el usuario desactivó el aviso."""

    def __init__(
        self,
        session: AsyncSession,
        templates: EmailTemplates | None = None,
        website_domain: str = settings.website_domain,
    ) -> None:
        self.interviews = InterviewRepository(session)
        self.templates = templates or EmailTemplates()
        self.website = website_domain.rstrip("/")

    async def compose(
        self, delivery: NotificationDelivery, user: User, unsubscribe_link: str
    ) -> RenderedEmail | None:
        parsed = interview_from_key(delivery.dedupe_key)
        if parsed is None or not user.notify_interview:
            return None
        interview_id, seconds = parsed
        row = await self.interviews.get_for_notification(user.id, interview_id)
        if row is None:
            return None
        interview, application, company = row
        if (
            interview.outcome != InterviewOutcome.PENDING
            or int(interview.scheduled_at.timestamp()) != seconds
        ):
            return None

        language = email_language(user.language)
        return self.templates.render(
            KIND.value,
            language,
            {
                # Texto del usuario en el asunto: una sola línea (ver reminder_due).
                "position": " ".join(application.position_title.split()),
                "company": " ".join(company.name.split()),
                "when": format_local_datetime(
                    interview.scheduled_at, user.timezone, language
                ),
                "interview_type": interview.interview_type,
                "format": interview.format,
                "duration_minutes": interview.duration_minutes,
                "interviewers": interview.interviewers,
                "link": f"{self.website}/applications/{application.id}",
                "preferences_link": f"{self.website}/preferences",
                "unsubscribe_link": unsubscribe_link,
            },
        )
