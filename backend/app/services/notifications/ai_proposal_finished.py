"""Aviso de propuesta de IA terminada (RF-157, decisión 0021): el barrido que lo
reclama y el compositor que escribe el email. Desactivado por defecto: casi siempre
se espera en la página, y la aplicación ya avisa dentro."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.ai import ProposalStatus
from app.domain.notifications import (
    AI_PROPOSAL_WINDOW,
    NotificationKind,
    ai_proposal_id_from_key,
    ai_proposal_key,
)
from app.domain.user import email_language
from app.infra.email.templates import EmailTemplates, RenderedEmail
from app.infra.queue import JobQueue
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.ai_proposal_repository import AiProposalRepository
from app.repositories.identity_repository import IdentityRepository
from app.services.notification_delivery_service import SingleDeliveryComposer
from app.services.notifications.sweep import ClaimingSweep, Cursor, SweepCandidate

KIND = NotificationKind.AI_PROPOSAL_FINISHED


class AiProposalFinishedSweep:
    """Barrido de RF-157, cada minuto: un aviso por propuesta terminada en la
    última hora, de cuentas con el aviso activado y el email verificado."""

    def __init__(
        self,
        session: AsyncSession,
        job_queue: JobQueue,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.proposals = AiProposalRepository(session)
        self.sweep = ClaimingSweep(session, job_queue, identities)

    async def run(self, now: datetime) -> int:
        async def fetch_page(after: Cursor | None, limit: int) -> list[SweepCandidate]:
            finished = await self.proposals.list_finished_for_notification(
                finished_after=now - AI_PROPOSAL_WINDOW,
                now=now,
                after=after,
                limit=limit,
            )
            return [
                SweepCandidate(
                    user_id=row.user_id,
                    supertokens_user_id=row.supertokens_user_id,
                    dedupe_key=ai_proposal_key(row.proposal_id),
                    cursor=(row.finished_at, row.proposal_id),
                )
                for row in finished
            ]

        return await self.sweep.claim_all(KIND, fetch_page, now)


class AiProposalFinishedComposer(SingleDeliveryComposer):
    """Escribe el email: lista para revisar o por qué no salió, con un enlace.
    **Nunca** lleva el contenido de la propuesta (son datos del perfil). None si
    ya no hay nada que avisar: el usuario desactivó el aviso, o borró la solicitud
    (y con ella la propuesta), entre el barrido y el envío."""

    def __init__(
        self,
        session: AsyncSession,
        templates: EmailTemplates | None = None,
        website_domain: str = settings.website_domain,
    ) -> None:
        self.proposals = AiProposalRepository(session)
        self.templates = templates or EmailTemplates()
        self.website = website_domain.rstrip("/")

    async def compose_one(
        self, delivery: NotificationDelivery, user: User, unsubscribe_link: str
    ) -> RenderedEmail | None:
        proposal_id = ai_proposal_id_from_key(delivery.dedupe_key)
        if proposal_id is None or not user.notify_ai_proposal:
            return None
        notice = await self.proposals.get_for_notification(user.id, proposal_id)
        if notice is None:
            return None

        proposal = notice.proposal
        application_link = f"{self.website}/applications/{proposal.application_id}"
        succeeded = proposal.status == ProposalStatus.SUCCEEDED
        return self.templates.render(
            KIND.value,
            email_language(user.language),
            {
                "kind": proposal.kind,
                "succeeded": succeeded,
                "error_code": proposal.error_code or "ai_interrupted",
                # Los escribe el usuario y van en el asunto: un salto de línea en
                # una cabecera haría que el SMTP lo rechazara.
                "position": " ".join(notice.position_title.split()),
                "company": " ".join(notice.company_name.split()),
                "link": (
                    f"{application_link}/ai/{proposal.id}"
                    if succeeded
                    else application_link
                ),
                "preferences_link": f"{self.website}/preferences",
                "unsubscribe_link": unsubscribe_link,
            },
        )
