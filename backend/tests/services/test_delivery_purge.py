"""Limpieza de entregas antiguas (F12): borrar una entrega le quita a su motivo la
protección de "nunca dos veces", así que solo se borra lo que ningún barrido puede
volver a encontrar. Una prueba por tipo de aviso lo demuestra.

"Ahora" es un lunes lejos del reloj real: los barridos recorren a todos los
usuarios, y así no ven datos de otras pruebas.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import (
    DeliveryStatus,
    NotificationKind,
    interview_key,
    reminder_due_key,
    stale_key,
)
from app.infra.queue import InMemoryJobQueue
from app.repositories.identity_repository import IdentityRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.notifications import (
    InterviewUpcomingSweep,
    ReminderDueSweep,
    StaleApplicationSweep,
    WeeklyDigestSweep,
)
from tests.factories import (
    make_application,
    make_company,
    make_interview,
    make_reminder,
)

NOW = datetime(2031, 3, 10, 9, 0, tzinfo=UTC)
OLD = NOW - timedelta(days=91)


class VerifiedIdentities(IdentityRepository):
    async def is_email_verified(self, supertokens_user_id: str) -> bool:
        return True


async def _finished(
    session: AsyncSession,
    user: CurrentUser,
    kind: NotificationKind,
    key: str,
    *,
    claimed_at: datetime = OLD,
    status: DeliveryStatus = DeliveryStatus.SENT,
    next_attempt_at: datetime | None = None,
) -> uuid.UUID:
    repository = NotificationDeliveryRepository(session)
    delivery_id = await repository.claim(user.id, kind, key, claimed_at)
    assert delivery_id is not None
    delivery = await repository.get(delivery_id, user.id)
    assert delivery is not None
    delivery.status = status
    delivery.next_attempt_at = next_attempt_at
    await repository.save(delivery)
    return delivery_id


async def _purge(session: AsyncSession) -> int:
    return await NotificationDeliveryService(session).purge_old_deliveries(NOW)


async def _exists(
    session: AsyncSession, user: CurrentUser, delivery_id: uuid.UUID
) -> bool:
    return (
        await NotificationDeliveryRepository(session).get(delivery_id, user.id)
        is not None
    )


@pytest.mark.asyncio
async def test_only_old_finished_deliveries_are_purged(
    db_session: AsyncSession, user: CurrentUser
):
    kind = NotificationKind.REMINDER_DUE
    purged = [
        await _finished(db_session, user, kind, "a", status=DeliveryStatus.SENT),
        await _finished(db_session, user, kind, "b", status=DeliveryStatus.UNKNOWN),
        await _finished(db_session, user, kind, "c", status=DeliveryStatus.FAILED),
    ]
    kept = [
        # Reciente.
        await _finished(
            db_session, user, kind, "d", claimed_at=NOW - timedelta(days=89)
        ),
        # En curso: lo decide el barrido de reclamos abandonados.
        await _finished(db_session, user, kind, "e", status=DeliveryStatus.CLAIMED),
        # Fallida con un reintento pendiente.
        await _finished(
            db_session,
            user,
            kind,
            "f",
            status=DeliveryStatus.FAILED,
            next_attempt_at=NOW,
        ),
    ]

    await _purge(db_session)

    assert [await _exists(db_session, user, d) for d in purged] == [False] * 3
    assert [await _exists(db_session, user, d) for d in kept] == [True] * 3


@pytest.mark.asyncio
async def test_a_purged_reminder_is_not_notified_again(
    db_session: AsyncSession, user: CurrentUser
):
    reminder = await make_reminder(db_session, user.id, due_at=OLD)
    await _finished(
        db_session, user, NotificationKind.REMINDER_DUE, reminder_due_key(reminder.id)
    )
    # Con la antelación máxima, el momento del aviso se adelanta 7 días: sigue lejos.
    account = await UserRepository(db_session).get_by_id(user.id)
    assert account is not None
    account.reminder_notice_hours = 168

    await _purge(db_session)
    claimed = await ReminderDueSweep(
        db_session, InMemoryJobQueue(), VerifiedIdentities()
    ).run(NOW)

    assert claimed == 0


@pytest.mark.asyncio
async def test_a_purged_interview_is_not_notified_again(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    interview = await make_interview(
        db_session, application, scheduled_at=OLD + timedelta(days=1)
    )
    await _finished(
        db_session,
        user,
        NotificationKind.INTERVIEW_UPCOMING,
        interview_key(interview.id, interview.scheduled_at),
    )

    await _purge(db_session)
    claimed = await InterviewUpcomingSweep(
        db_session, InMemoryJobQueue(), VerifiedIdentities()
    ).run(NOW)

    assert claimed == 0


@pytest.mark.asyncio
async def test_a_purged_digest_does_not_repeat_its_week(
    db_session: AsyncSession, user: CurrentUser
):
    account = await UserRepository(db_session).get_by_id(user.id)
    assert account is not None
    account.notify_weekly_digest = True
    old_week = await _finished(
        db_session, user, NotificationKind.WEEKLY_DIGEST, "digest:2030-W49"
    )

    await _purge(db_session)
    queue = InMemoryJobQueue()
    claimed = await WeeklyDigestSweep(db_session, queue, VerifiedIdentities()).run(NOW)

    # Solo el de esta semana: el de diciembre no puede volver a tocar.
    assert not await _exists(db_session, user, old_week)
    assert claimed == 1


@pytest.mark.asyncio
async def test_a_still_stale_application_keeps_its_delivery_forever(
    db_session: AsyncSession, user: CurrentUser
):
    # El barrido de inactividad no tiene ventana: si se borrara la entrega de una
    # solicitud que sigue parada, se volvería a avisar cada 90 días.
    account = await UserRepository(db_session).get_by_id(user.id)
    assert account is not None
    account.notify_stale = True
    forgotten = await make_application(
        db_session,
        user.id,
        await make_company(db_session, user.id),
        status="applied",
        last_activity_at=NOW - timedelta(days=200),
    )
    kept = await _finished(
        db_session,
        user,
        NotificationKind.STALE_APPLICATION,
        stale_key(forgotten.id, forgotten.last_activity_at),
    )
    moved = await make_application(
        db_session,
        user.id,
        await make_company(db_session, user.id),
        status="applied",
        last_activity_at=NOW - timedelta(days=1),
    )
    outdated = await _finished(
        db_session,
        user,
        NotificationKind.STALE_APPLICATION,
        stale_key(moved.id, NOW - timedelta(days=200)),
    )

    await _purge(db_session)
    claimed = await StaleApplicationSweep(
        db_session, InMemoryJobQueue(), VerifiedIdentities()
    ).run(NOW)

    assert await _exists(db_session, user, kept)
    # La de un periodo que ya terminó no puede volver a coincidir: se borra.
    assert not await _exists(db_session, user, outdated)
    assert claimed == 0
