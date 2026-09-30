"""Reclamos de entregas de avisos (RF-87, segundo plano §4: B3, B6)."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import DeliveryStatus, NotificationKind
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import NotificationDeliveryService
from tests.conftest import create_test_user, test_engine

NOW = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)
KIND = NotificationKind.REMINDER_DUE


async def _reload(
    session: AsyncSession, delivery_id: uuid.UUID, user: CurrentUser
) -> NotificationDelivery:
    delivery = await NotificationDeliveryRepository(session).get(delivery_id, user.id)
    assert delivery is not None
    await session.refresh(delivery)
    return delivery


@pytest.mark.asyncio
async def test_the_same_reason_is_claimed_only_once(
    db_session: AsyncSession, user: CurrentUser
):
    repository = NotificationDeliveryRepository(db_session)

    first = await repository.claim(user.id, KIND, "reminder:1", NOW)
    second = await repository.claim(user.id, KIND, "reminder:1", NOW)

    assert first is not None
    assert second is None
    delivery = await _reload(db_session, first, user)
    assert delivery.status == DeliveryStatus.CLAIMED
    assert delivery.attempts == 1


@pytest.mark.asyncio
async def test_another_reason_kind_or_user_is_another_claim(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    repository = NotificationDeliveryRepository(db_session)
    await repository.claim(user.id, KIND, "reminder:1", NOW)

    assert await repository.claim(user.id, KIND, "reminder:2", NOW) is not None
    assert (
        await repository.claim(
            user.id, NotificationKind.INTERVIEW_UPCOMING, "reminder:1", NOW
        )
        is not None
    )
    assert await repository.claim(other_user.id, KIND, "reminder:1", NOW) is not None


@pytest.mark.asyncio
async def test_a_failed_delivery_is_reclaimed_only_when_its_retry_is_due(
    db_session: AsyncSession, user: CurrentUser
):
    repository = NotificationDeliveryRepository(db_session)
    delivery_id = await repository.claim(user.id, KIND, "reminder:1", NOW)
    assert delivery_id is not None
    delivery = await _reload(db_session, delivery_id, user)
    delivery.status = DeliveryStatus.FAILED
    delivery.next_attempt_at = NOW + timedelta(minutes=5)
    await repository.save(delivery)

    too_early = await repository.claim(
        user.id, KIND, "reminder:1", NOW + timedelta(minutes=4)
    )
    due = await repository.claim(
        user.id, KIND, "reminder:1", NOW + timedelta(minutes=5)
    )

    assert too_early is None
    assert due == delivery_id
    delivery = await _reload(db_session, delivery_id, user)
    assert delivery.status == DeliveryStatus.CLAIMED
    assert delivery.attempts == 2
    assert delivery.next_attempt_at is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [DeliveryStatus.SENT, DeliveryStatus.UNKNOWN])
async def test_sent_or_unknown_deliveries_are_never_reclaimed(
    db_session: AsyncSession, user: CurrentUser, status: DeliveryStatus
):
    repository = NotificationDeliveryRepository(db_session)
    delivery_id = await repository.claim(user.id, KIND, "reminder:1", NOW)
    assert delivery_id is not None
    delivery = await _reload(db_session, delivery_id, user)
    delivery.status = status
    await repository.save(delivery)

    assert (
        await repository.claim(user.id, KIND, "reminder:1", NOW + timedelta(days=30))
        is None
    )


@pytest.mark.asyncio
async def test_failed_delivery_without_retries_left_is_never_reclaimed(
    db_session: AsyncSession, user: CurrentUser
):
    repository = NotificationDeliveryRepository(db_session)
    delivery_id = await repository.claim(user.id, KIND, "reminder:1", NOW)
    assert delivery_id is not None
    delivery = await _reload(db_session, delivery_id, user)
    delivery.status = DeliveryStatus.FAILED
    delivery.next_attempt_at = None
    await repository.save(delivery)

    assert (
        await repository.claim(user.id, KIND, "reminder:1", NOW + timedelta(days=30))
        is None
    )


@pytest.mark.asyncio
async def test_get_does_not_return_another_users_delivery(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    repository = NotificationDeliveryRepository(db_session)
    delivery_id = await repository.claim(user.id, KIND, "reminder:1", NOW)
    assert delivery_id is not None

    assert await repository.get(delivery_id, other_user.id) is None


@pytest.mark.asyncio
async def test_abandoned_claims_become_unknown_and_recent_ones_stay(
    db_session: AsyncSession, user: CurrentUser
):
    # B6: un proceso que murió a mitad no deja el aviso pendiente de reenviarse.
    repository = NotificationDeliveryRepository(db_session)
    old = await repository.claim(user.id, KIND, "reminder:old", NOW)
    recent = await repository.claim(
        user.id, KIND, "reminder:recent", NOW + timedelta(minutes=9)
    )
    assert old is not None and recent is not None

    expired = await repository.expire_abandoned_claims(NOW + timedelta(minutes=5))

    assert expired == 1
    assert (await _reload(db_session, old, user)).status == DeliveryStatus.UNKNOWN
    assert (await _reload(db_session, recent, user)).status == DeliveryStatus.CLAIMED
    # Y un reclamo ya en unknown no se puede volver a reclamar.
    assert (
        await repository.claim(user.id, KIND, "reminder:old", NOW + timedelta(days=1))
        is None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "channel", "status"),
    [
        ("birthday", "email", DeliveryStatus.CLAIMED),
        # Un canal nuevo necesita su migración: la BD no admite uno a medias.
        (KIND, "telegram", DeliveryStatus.CLAIMED),
        (KIND, "email", "delivered"),
    ],
)
async def test_database_rejects_unknown_kind_channel_or_status(
    db_session: AsyncSession, user: CurrentUser, kind: str, channel: str, status: str
):
    db_session.add(
        NotificationDelivery(
            user_id=user.id,
            kind=kind,
            channel=channel,
            dedupe_key="x",
            status=status,
            claimed_at=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_two_simultaneous_sweeps_claim_a_reason_once():
    # B3: dos barridos a la vez sobre el mismo recordatorio. Necesita dos
    # transacciones reales (la clave única de una bloquea a la otra hasta su
    # commit), así que no usa db_session y limpia al final.
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        await setup.commit()
    session_a = AsyncSession(test_engine, expire_on_commit=False)
    session_b = AsyncSession(test_engine, expire_on_commit=False)
    try:
        results = await asyncio.gather(
            NotificationDeliveryService(session_a).claim(
                owner.id, KIND, "reminder:race", NOW
            ),
            NotificationDeliveryService(session_b).claim(
                owner.id, KIND, "reminder:race", NOW
            ),
        )

        async with AsyncSession(test_engine) as check:
            count = await check.scalar(
                select(func.count())
                .select_from(NotificationDelivery)
                .where(NotificationDelivery.user_id == owner.id)
            )

        assert sorted(r is None for r in results) == [False, True]
        assert count == 1
    finally:
        await session_a.close()
        await session_b.close()
        async with AsyncSession(test_engine) as cleanup:
            await cleanup.execute(delete(User).where(User.id == owner.id))
            await cleanup.commit()
