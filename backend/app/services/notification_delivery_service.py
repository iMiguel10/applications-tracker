import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.domain.notifications import (
    ABANDONED_CLAIM_AFTER,
    MAX_DELIVERY_ATTEMPTS,
    DeliveryStatus,
    NotificationKind,
    next_attempt_at,
)
from app.domain.unsubscribe import unsubscribe_token
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


@dataclass(frozen=True)
class Composition:
    """Un email y las entregas que cubre. Un email suele cubrir una entrega; el de
    solicitudes sin actividad (RF-83) cubre una por solicitud de la lista."""

    email: RenderedEmail
    covers: Sequence[NotificationDelivery]


class NotificationComposer(Protocol):
    """Escribe el email de un lote de entregas del mismo tipo y usuario (el motivo
    de cada una va en `dedupe_key`). Las entregas que el email no cubre son motivos
    que ya no existen (un recordatorio que se completó entre el barrido y el envío)
    y se borran; None si no queda ninguno.

    `unsubscribe_link` es la página de baja de ese tipo (RF-85): todo email de
    aviso la lleva."""

    async def compose(
        self,
        deliveries: Sequence[NotificationDelivery],
        user: User,
        unsubscribe_link: str,
    ) -> Composition | None: ...


class SingleDeliveryComposer(ABC):
    """Base de los avisos de un motivo por email (recordatorio, entrevista): sus
    lotes son siempre de una entrega."""

    async def compose(
        self,
        deliveries: Sequence[NotificationDelivery],
        user: User,
        unsubscribe_link: str,
    ) -> Composition | None:
        [delivery] = deliveries
        email = await self.compose_one(delivery, user, unsubscribe_link)
        return Composition(email, [delivery]) if email is not None else None

    @abstractmethod
    async def compose_one(
        self, delivery: NotificationDelivery, user: User, unsubscribe_link: str
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
        config: Settings = settings,
    ) -> None:
        self.session = session
        self.deliveries = NotificationDeliveryRepository(session)
        self.config = config
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
        self,
        job_queue: JobQueue,
        delivery_ids: Sequence[uuid.UUID],
        user_id: uuid.UUID,
    ) -> None:
        """Encola el envío de un email que cubre estas entregas, ya confirmadas y
        del mismo tipo y usuario (invariante 11). Si la cola no responde, se quedan
        en `claimed` y el barrido de reclamos abandonados las da por perdidas: se
        pierde un email, nunca se duplica."""
        try:
            await job_queue.enqueue(
                SEND_NOTIFICATION,
                timeout_seconds=SEND_NOTIFICATION_TIMEOUT_SECONDS,
                max_attempts=1,
                key=f"notification:{delivery_ids[0]}",
                delivery_ids=",".join(str(delivery_id) for delivery_id in delivery_ids),
                user_id=str(user_id),
            )
        except QueueUnavailableError:
            logger.warning("Envío de las entregas %s sin encolar", delivery_ids)

    async def deliver(
        self,
        delivery_ids: Sequence[uuid.UUID],
        user_id: uuid.UUID,
        now: datetime,
    ) -> None:
        """Envía un email con las entregas reclamadas de la lista. Idempotente: las
        que ya no están en `claimed` (se enviaron, o un barrido las dio por
        abandonadas) no se tocan, y sin ninguna no se envía nada."""
        assert self.email_sender is not None, "deliver necesita un EmailSender"
        deliveries = [
            delivery
            for delivery in await self.deliveries.get_many(delivery_ids, user_id)
            if delivery.status == DeliveryStatus.CLAIMED
        ]
        if not deliveries:
            logger.info("Entregas %s ya no están reclamadas; se ignoran", delivery_ids)
            return
        kind = NotificationKind(deliveries[0].kind)
        assert all(delivery.kind == kind for delivery in deliveries)

        composer = self.composers.get(kind)
        user = await self.users.get_by_id(user_id)
        if composer is None or user is None:
            logger.error("Entregas de tipo %s sin compositor", kind)
            await self._give_up(deliveries)
            return
        address = await self.identities.get_email(user.supertokens_user_id)
        if address is None:
            # La cuenta se borró entre el barrido y el envío (segundo plano §5).
            await self._give_up(deliveries)
            return
        token = unsubscribe_token(user.id, kind, self.config.app_secret)
        composition = await composer.compose(
            deliveries,
            user,
            f"{self.config.website_domain.rstrip('/')}/unsubscribe?token={token}",
        )
        covered = composition.covers if composition is not None else []
        covered_ids = {delivery.id for delivery in covered}
        for delivery in deliveries:
            if delivery.id not in covered_ids:
                # El motivo desapareció y no salió nada: no hay nada que recordar.
                await self.deliveries.delete(delivery)
        if composition is None:
            await self.session.commit()
            return

        one_click = (
            f"{self.config.api_domain.rstrip('/')}"
            f"/api/v1/notifications/unsubscribe?token={token}"
        )
        email = OutgoingEmail(
            to=address,
            subject=composition.email.subject,
            text=composition.email.text,
            html=composition.email.html,
            # RFC 2369 y 8058: el botón de baja de los clientes de correo hace un
            # POST a esta URL. La página del enlace del pie, en cambio, pide
            # confirmar: un escáner de enlaces solo hace GET.
            headers={
                "List-Unsubscribe": f"<{one_click}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
        # Un solo email: el resultado vale para todas las entregas que cubre.
        try:
            await self.email_sender.send(email)
        except EmailDeliveryUnknownError:
            for delivery in covered:
                delivery.status = DeliveryStatus.UNKNOWN
            logger.warning("Entregas %s: no se sabe si salieron", covered_ids)
        except EmailNotSentError:
            for delivery in covered:
                delivery.status = DeliveryStatus.FAILED
                delivery.next_attempt_at = next_attempt_at(delivery.attempts, now)
            logger.warning(
                "Entregas %s no enviadas (máximo %d intentos)",
                covered_ids,
                MAX_DELIVERY_ATTEMPTS,
                exc_info=True,
            )
        else:
            for delivery in covered:
                delivery.status = DeliveryStatus.SENT
                delivery.sent_at = now
            logger.info("Entregas %s enviadas", covered_ids)
        await self.session.flush()
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

    async def _give_up(self, deliveries: Sequence[NotificationDelivery]) -> None:
        # No salieron y reintentarlo no cambiaría nada: fallidas sin más intentos.
        for delivery in deliveries:
            delivery.status = DeliveryStatus.FAILED
            delivery.next_attempt_at = None
        await self.session.flush()
        await self.session.commit()
