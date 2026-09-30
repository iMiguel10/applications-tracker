import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import DeliveryChannel, DeliveryStatus, NotificationKind
from app.models.notification_delivery import NotificationDelivery


class NotificationDeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim(
        self,
        user_id: uuid.UUID,
        kind: NotificationKind,
        dedupe_key: str,
        now: datetime,
        channel: DeliveryChannel = DeliveryChannel.EMAIL,
    ) -> uuid.UUID | None:
        """Reclama el envío de un aviso y devuelve el id de la entrega, o None si
        otro ya lo tiene (RF-87, segundo plano §4).

        Las dos sentencias son atómicas por sí solas, sin bloqueo previo: de dos
        barridos simultáneos, uno inserta y el otro choca con la clave única; y de
        dos que quieren reintentar la misma entrega fallida, solo uno encuentra aún
        la fila en `failed`. Cada reclamo cuenta como un intento.
        """
        inserted = await self.session.scalar(
            insert(NotificationDelivery)
            .values(
                user_id=user_id,
                kind=kind,
                channel=channel,
                dedupe_key=dedupe_key,
                status=DeliveryStatus.CLAIMED,
                attempts=1,
                claimed_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    NotificationDelivery.user_id,
                    NotificationDelivery.kind,
                    NotificationDelivery.channel,
                    NotificationDelivery.dedupe_key,
                ]
            )
            .returning(NotificationDelivery.id)
        )
        if inserted is not None:
            return inserted
        # Ya existe: solo se vuelve a reclamar si falló ANTES de salir y ya toca
        # reintentarlo. `sent` y `unknown` no se tocan nunca.
        return await self.session.scalar(
            update(NotificationDelivery)
            .where(
                NotificationDelivery.user_id == user_id,
                NotificationDelivery.kind == kind,
                NotificationDelivery.channel == channel,
                NotificationDelivery.dedupe_key == dedupe_key,
                NotificationDelivery.status == DeliveryStatus.FAILED,
                NotificationDelivery.next_attempt_at <= now,
            )
            .values(
                status=DeliveryStatus.CLAIMED,
                attempts=NotificationDelivery.attempts + 1,
                claimed_at=now,
                next_attempt_at=None,
            )
            .returning(NotificationDelivery.id)
        )

    async def get(
        self, delivery_id: uuid.UUID, user_id: uuid.UUID
    ) -> NotificationDelivery | None:
        return await self.session.scalar(
            select(NotificationDelivery).where(
                NotificationDelivery.id == delivery_id,
                NotificationDelivery.user_id == user_id,
            )
        )

    async def save(self, delivery: NotificationDelivery) -> NotificationDelivery:
        await self.session.flush()
        return delivery

    async def delete(self, delivery: NotificationDelivery) -> None:
        await self.session.delete(delivery)
        await self.session.flush()

    async def expire_abandoned_claims(self, claimed_before: datetime) -> int:
        """Pasa a `unknown` los reclamos que siguen en `claimed` desde antes de
        `claimed_before`: el proceso que los tenía murió a mitad y no se sabe si
        el email salió, así que nunca se reenvían (segundo plano §4, B6).

        Recorre las entregas de todos los usuarios a propósito: es un barrido del
        sistema, no devuelve datos de nadie y solo cambia el estado.
        """
        result = await self.session.execute(
            update(NotificationDelivery)
            .where(
                NotificationDelivery.status == DeliveryStatus.CLAIMED,
                NotificationDelivery.claimed_at < claimed_before,
            )
            .values(status=DeliveryStatus.UNKNOWN)
        )
        return int(getattr(result, "rowcount", 0) or 0)
