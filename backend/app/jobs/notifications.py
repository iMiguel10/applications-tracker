"""Avisos por email (F12, RF-80…87). Los barridos programados reclaman y encolan;
`send_notification` envía una entrega ya reclamada (segundo plano §3 y §4)."""

import uuid
from datetime import UTC, datetime

from saq import CronJob

from app.jobs.context import WorkerContext
from app.services.notification_delivery_service import NotificationDeliveryService

# Segundo plano §2: un barrido tiene 50 s y un solo intento; si falla, lo repite
# la siguiente pasada.
SWEEP_TIMEOUT_SECONDS = 50


async def send_notification(
    ctx: WorkerContext, *, delivery_id: str, user_id: str
) -> None:
    async with ctx["session_factory"]() as session:
        service = NotificationDeliveryService(session, email_sender=ctx["email_sender"])
        await service.deliver(uuid.UUID(delivery_id), uuid.UUID(user_id), _now())


async def expire_abandoned_notification_claims(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await NotificationDeliveryService(session).expire_abandoned_claims(_now())


def notification_cron_jobs(email_enabled: bool) -> list[CronJob[WorkerContext]]:
    """Los barridos de avisos. Sin SMTP no se programa ninguno (RNF-34, B11): no
    tendría sentido reclamar emails que nunca van a salir."""
    if not email_enabled:
        return []
    return [
        CronJob(
            expire_abandoned_notification_claims,
            cron="*/5 * * * *",
            timeout=SWEEP_TIMEOUT_SECONDS,
            retries=1,
        ),
    ]


def _now() -> datetime:
    # Los services reciben "ahora" como parámetro para que las pruebas usen fechas
    # fijas (segundo plano §3); el reloj real solo se lee aquí.
    return datetime.now(UTC)
