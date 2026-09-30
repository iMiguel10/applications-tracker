import logging
import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import (
    ABANDONED_CLAIM_AFTER,
    MAX_DELIVERY_ATTEMPTS,
    DeliveryStatus,
    NotificationKind,
    next_attempt_at,
)
from app.infra.email import (
    EmailDeliveryUnknownError,
    EmailNotSentError,
    EmailSender,
    OutgoingEmail,
)
from app.infra.email.templates import RenderedEmail
from app.infra.queue import JobQueue, QueueUnavailableError
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

SEND_NOTIFICATION = "send_notification"
# Segundo plano §2: un email, 30 s y un solo intento en la cola. Quien decide si
# se reintenta es la máquina de estados de la entrega, que sabe dónde falló.
SEND_NOTIFICATION_TIMEOUT_SECONDS = 30


class NotificationComposer(Protocol):
    """Escribe el email de un tipo de aviso a partir de su entrega (el motivo va
    en `dedupe_key`). None si el motivo ya no existe: un recordatorio que se
    completó entre el barrido y el envío no debe avisar de nada."""

    async def compose(
        self, delivery: NotificationDelivery, user: User
    ) -> RenderedEmail | None: ...


class NotificationDeliveryService:
    """Entregas de avisos por email: "nunca dos veces" (RF-87, A20, segundo plano
    §4). Se reclama y se confirma en la BD antes de enviar, y el resultado del
    envío decide el estado: solo se reintenta lo que con seguridad no salió."""

    def __init__(
        self,
        session: AsyncSession,
        email_sender: EmailSender | None = None,
        composers: Mapping[NotificationKind, NotificationComposer] | None = None,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.session = session
        self.deliveries = NotificationDeliveryRepository(session)
        self.users = UserRepository(session)
        self.email_sender = email_sender
        self.composers = composers or {}
        self.identities = identities or IdentityRepository()

    async def claim(
        self,
        user_id: uuid.UUID,
        kind: NotificationKind,
        dedupe_key: str,
        now: datetime,
    ) -> uuid.UUID | None:
        """Reclama un aviso y lo confirma antes de que nadie hable con el SMTP.
        None si ya estaba reclamado (otro barrido, o un envío anterior)."""
        delivery_id = await self.deliveries.claim(user_id, kind, dedupe_key, now)
        await self.session.commit()
        return delivery_id

    async def enqueue_send(
        self, job_queue: JobQueue, delivery_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Encola el envío de una entrega ya confirmada (invariante 11). Si la cola
        no responde, la entrega se queda en `claimed` y el barrido de reclamos
        abandonados la da por perdida: se pierde un email, nunca se duplica."""
        try:
            await job_queue.enqueue(
                SEND_NOTIFICATION,
                timeout_seconds=SEND_NOTIFICATION_TIMEOUT_SECONDS,
                max_attempts=1,
                key=f"notification:{delivery_id}",
                delivery_id=str(delivery_id),
                user_id=str(user_id),
            )
        except QueueUnavailableError:
            logger.warning("Envío de la entrega %s sin encolar", delivery_id)

    async def deliver(
        self, delivery_id: uuid.UUID, user_id: uuid.UUID, now: datetime
    ) -> None:
        """Envía una entrega reclamada. Idempotente: si ya no está en `claimed`
        (se envió, o un barrido la dio por abandonada), no hace nada."""
        assert self.email_sender is not None, "deliver necesita un EmailSender"
        delivery = await self.deliveries.get(delivery_id, user_id)
        if delivery is None or delivery.status != DeliveryStatus.CLAIMED:
            logger.info("Entrega %s ya no está reclamada; se ignora", delivery_id)
            return

        composer = self.composers.get(NotificationKind(delivery.kind))
        user = await self.users.get_by_id(user_id)
        if composer is None or user is None:
            logger.error(
                "Entrega %s de tipo %s sin compositor", delivery.id, delivery.kind
            )
            await self._give_up(delivery)
            return
        address = await self.identities.get_email(user.supertokens_user_id)
        if address is None:
            # La cuenta se borró entre el barrido y el envío (segundo plano §5).
            await self._give_up(delivery)
            return
        content = await composer.compose(delivery, user)
        if content is None:
            # El motivo desapareció y no salió nada: no hay nada que recordar.
            await self.deliveries.delete(delivery)
            await self.session.commit()
            return

        email = OutgoingEmail(
            to=address, subject=content.subject, text=content.text, html=content.html
        )
        try:
            await self.email_sender.send(email)
        except EmailDeliveryUnknownError:
            delivery.status = DeliveryStatus.UNKNOWN
            logger.warning("Entrega %s: no se sabe si salió", delivery.id)
        except EmailNotSentError:
            delivery.status = DeliveryStatus.FAILED
            delivery.next_attempt_at = next_attempt_at(delivery.attempts, now)
            logger.warning(
                "Entrega %s no enviada (intento %d de %d)",
                delivery.id,
                delivery.attempts,
                MAX_DELIVERY_ATTEMPTS,
                exc_info=True,
            )
        else:
            delivery.status = DeliveryStatus.SENT
            delivery.sent_at = now
            logger.info("Entrega %s enviada", delivery.id)
        await self.deliveries.save(delivery)
        await self.session.commit()

    async def expire_abandoned_claims(self, now: datetime) -> int:
        """Barrido de reclamos abandonados: `claimed` pasado ABANDONED_CLAIM_AFTER
        pasa a `unknown` (B6)."""
        expired = await self.deliveries.expire_abandoned_claims(
            now - ABANDONED_CLAIM_AFTER
        )
        await self.session.commit()
        if expired:
            logger.warning("%d entregas abandonadas pasan a unknown", expired)
        return expired

    async def _give_up(self, delivery: NotificationDelivery) -> None:
        # No salió y reintentarlo no cambiaría nada: fallida sin más intentos.
        delivery.status = DeliveryStatus.FAILED
        delivery.next_attempt_at = None
        await self.deliveries.save(delivery)
        await self.session.commit()
