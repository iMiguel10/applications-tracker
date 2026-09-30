"""Avisos por email (F12, RF-80…87). Los barridos programados reclaman y encolan;
`send_notification` envía una entrega ya reclamada (segundo plano §3 y §4)."""

import uuid
from datetime import UTC, datetime

from saq import CronJob

from app.jobs.context import WorkerContext
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.notifications import (
    InterviewUpcomingSweep,
    ReminderDueSweep,
    StaleApplicationSweep,
    WeeklyDigestSweep,
    composers_for,
)

# Segundo plano §2: un barrido tiene 50 s y un solo intento; si falla, lo repite
# la siguiente pasada.
SWEEP_TIMEOUT_SECONDS = 50


async def send_notification(
    ctx: WorkerContext, *, delivery_ids: str, user_id: str
) -> None:
    async with ctx["session_factory"]() as session:
        service = NotificationDeliveryService(
            session,
            email_sender=ctx["email_sender"],
            composers=composers_for(session),
        )
        await service.deliver(
            [uuid.UUID(delivery_id) for delivery_id in delivery_ids.split(",")],
            uuid.UUID(user_id),
            _now(),
        )


async def sweep_due_reminders(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await ReminderDueSweep(session, ctx["job_queue"]).run(_now())


async def sweep_upcoming_interviews(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await InterviewUpcomingSweep(session, ctx["job_queue"]).run(_now())


async def sweep_stale_applications(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await StaleApplicationSweep(session, ctx["job_queue"]).run(_now())


async def sweep_weekly_digests(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await WeeklyDigestSweep(session, ctx["job_queue"]).run(_now())


async def expire_abandoned_notification_claims(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await NotificationDeliveryService(session).expire_abandoned_claims(_now())


async def purge_old_notification_deliveries(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await NotificationDeliveryService(session).purge_old_deliveries(_now())


def notification_cron_jobs(email_enabled: bool) -> list[CronJob[WorkerContext]]:
    """Los barridos de avisos. Sin SMTP no se programa ninguno (RNF-34, B11): no
    tendría sentido reclamar emails que nunca van a salir."""
    if not email_enabled:
        return []
    return [
        CronJob(
            sweep_due_reminders,
            cron="* * * * *",
            timeout=SWEEP_TIMEOUT_SECONDS,
            retries=1,
        ),
        CronJob(
            sweep_upcoming_interviews,
            cron="*/5 * * * *",
            timeout=SWEEP_TIMEOUT_SECONDS,
            retries=1,
        ),
        CronJob(
            sweep_stale_applications,
            cron="7 * * * *",
            timeout=SWEEP_TIMEOUT_SECONDS,
            retries=1,
        ),
        CronJob(
            sweep_weekly_digests,
            # Cada hora: sale en la primera pasada desde las 8:00 locales (a las
            # 8:30 en las zonas de media hora, como la India).
            cron="0 * * * *",
            timeout=SWEEP_TIMEOUT_SECONDS,
            retries=1,
        ),
        CronJob(
            expire_abandoned_notification_claims,
            cron="*/5 * * * *",
            timeout=SWEEP_TIMEOUT_SECONDS,
            retries=1,
        ),
        CronJob(
            purge_old_notification_deliveries,
            cron="30 3 * * *",
            timeout=SWEEP_TIMEOUT_SECONDS,
            retries=1,
        ),
    ]


def _now() -> datetime:
    # Los services reciben "ahora" como parámetro para que las pruebas usen fechas
    # fijas (segundo plano §3); el reloj real solo se lee aquí.
    return datetime.now(UTC)
