"""Pruebas adversas de los avisos por email (F12, segundo plano §4 y §7), añadidas
por el qa-verifier: carreras con transacciones reales, trabajos que se ejecutan
dos veces a la vez y entregas que apuntan a datos de otro usuario.

Las de carreras necesitan dos transacciones reales (no `db_session`), así que
confirman sus datos y los borran al final. "Ahora" es una fecha lejos del reloj
real y de la de otras pruebas, para que los barridos no vean nada más.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import (
    DeliveryStatus,
    NotificationKind,
    interview_key,
    reminder_due_key,
    stale_key,
)
from app.infra.email.base import OutgoingEmail
from app.infra.email.recording import RecordingEmailSender
from app.infra.email.templates import RenderedEmail
from app.infra.queue import InMemoryJobQueue
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import (
    NotificationDeliveryService,
    SingleDeliveryComposer,
)
from app.services.notifications import ReminderDueSweep, composers_for
from tests.conftest import create_test_user, test_engine
from tests.factories import (
    make_application,
    make_company,
    make_interview,
    make_reminder,
)

NOW = datetime(2034, 6, 5, 9, 0, tzinfo=UTC)


class FakeIdentities(IdentityRepository):
    async def is_email_verified(self, supertokens_user_id: str) -> bool:
        return True

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return f"{supertokens_user_id}@example.com"


class SlowSender(RecordingEmailSender):
    """Un SMTP que tarda en aceptar: deja a la vista la ventana entre leer la
    entrega y marcarla como enviada."""

    async def send(self, email: OutgoingEmail) -> None:
        await asyncio.sleep(0.3)
        await super().send(email)


class FixedComposer(SingleDeliveryComposer):
    async def compose_one(
        self, delivery: NotificationDelivery, user: User, unsubscribe_link: str
    ) -> RenderedEmail | None:
        return RenderedEmail(subject="Aviso", text="Texto", html="<p>Texto</p>")


async def _delete_user(user_id: uuid.UUID) -> None:
    async with AsyncSession(test_engine) as cleanup:
        await cleanup.execute(delete(User).where(User.id == user_id))
        await cleanup.commit()


async def _count_deliveries(user_id: uuid.UUID) -> int:
    async with AsyncSession(test_engine) as check:
        return int(
            await check.scalar(
                select(func.count())
                .select_from(NotificationDelivery)
                .where(NotificationDelivery.user_id == user_id)
            )
            or 0
        )


# --- Carreras con transacciones reales -----------------------------------------


@pytest.mark.asyncio
async def test_two_simultaneous_reminder_sweeps_queue_a_single_send():
    # B3 de punta a punta: no solo el reclamo, también el barrido entero. Dos
    # workers disparan la misma pasada a la vez y solo uno encola el envío.
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        await make_reminder(setup, owner.id, due_at=NOW - timedelta(minutes=2))
        await setup.commit()
    session_a = AsyncSession(test_engine, expire_on_commit=False)
    session_b = AsyncSession(test_engine, expire_on_commit=False)
    queue_a, queue_b = InMemoryJobQueue(), InMemoryJobQueue()
    try:
        claimed = await asyncio.gather(
            ReminderDueSweep(session_a, queue_a, FakeIdentities()).run(NOW),
            ReminderDueSweep(session_b, queue_b, FakeIdentities()).run(NOW),
        )

        assert sorted(claimed) == [0, 1]
        assert len(queue_a.jobs) + len(queue_b.jobs) == 1
        assert await _count_deliveries(owner.id) == 1
    finally:
        await session_a.close()
        await session_b.close()
        await _delete_user(owner.id)


@pytest.mark.asyncio
async def test_the_same_send_job_running_twice_at_once_sends_one_email():
    # "Nunca dos veces" (RF-87) cuando el mismo trabajo de envío se ejecuta dos
    # veces a la vez (segundo plano §2, trampa del worker que toma por abandonado
    # un trabajo que acaba de empezar). Lo que no debe repetirse pasa por la BD,
    # no por la cola: la entrega tendría que impedir el segundo envío.
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        delivery_id = await NotificationDeliveryService(setup).claim(
            owner.id, NotificationKind.REMINDER_DUE, "reminder:race-send", NOW
        )
        assert delivery_id is not None
    sender = SlowSender()
    session_a = AsyncSession(test_engine, expire_on_commit=False)
    session_b = AsyncSession(test_engine, expire_on_commit=False)

    def service(session: AsyncSession) -> NotificationDeliveryService:
        return NotificationDeliveryService(
            session,
            email_sender=sender,
            composers={NotificationKind.REMINDER_DUE: FixedComposer()},
            identities=FakeIdentities(),
        )

    try:
        await asyncio.gather(
            service(session_a).deliver([delivery_id], owner.id, NOW),
            service(session_b).deliver([delivery_id], owner.id, NOW),
        )

        assert len(sender.sent) == 1
    finally:
        await session_a.close()
        await session_b.close()
        await _delete_user(owner.id)


# --- Entregas que apuntan a datos de otro usuario --------------------------------


def _deliverer(
    session: AsyncSession, sender: RecordingEmailSender
) -> NotificationDeliveryService:
    return NotificationDeliveryService(
        session,
        email_sender=sender,
        composers=composers_for(session),
        identities=FakeIdentities(),
    )


async def _assert_nothing_sent_and_claim_gone(
    session: AsyncSession,
    sender: RecordingEmailSender,
    delivery_id: uuid.UUID,
    user: CurrentUser,
) -> None:
    assert sender.sent == []
    assert await NotificationDeliveryRepository(session).get(delivery_id, user.id) is (
        None
    )


@pytest.mark.asyncio
async def test_a_delivery_keyed_to_another_users_reminder_sends_nothing(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    # Una clave manipulada no convierte a un usuario en lector de lo de otro: el
    # compositor carga el motivo por id **y** user_id.
    foreign = await make_reminder(
        db_session, other_user.id, due_at=NOW - timedelta(minutes=1)
    )
    sender = RecordingEmailSender()
    service = _deliverer(db_session, sender)
    delivery_id = await service.claim(
        user.id, NotificationKind.REMINDER_DUE, reminder_due_key(foreign.id), NOW
    )
    assert delivery_id is not None

    await service.deliver([delivery_id], user.id, NOW)

    await _assert_nothing_sent_and_claim_gone(db_session, sender, delivery_id, user)


@pytest.mark.asyncio
async def test_a_delivery_keyed_to_another_users_interview_sends_nothing(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    application = await make_application(db_session, other_user.id)
    scheduled_at = NOW + timedelta(hours=3)
    foreign = await make_interview(db_session, application, scheduled_at=scheduled_at)
    sender = RecordingEmailSender()
    service = _deliverer(db_session, sender)
    delivery_id = await service.claim(
        user.id,
        NotificationKind.INTERVIEW_UPCOMING,
        interview_key(foreign.id, scheduled_at),
        NOW,
    )
    assert delivery_id is not None

    await service.deliver([delivery_id], user.id, NOW)

    await _assert_nothing_sent_and_claim_gone(db_session, sender, delivery_id, user)


@pytest.mark.asyncio
async def test_a_delivery_keyed_to_another_users_application_sends_nothing(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    loaded = await UserRepository(db_session).get_by_id(user.id)
    assert loaded is not None
    loaded.notify_stale = True
    last_activity_at = NOW - timedelta(days=60)
    company = await make_company(db_session, other_user.id)
    foreign = await make_application(
        db_session, other_user.id, company, last_activity_at=last_activity_at
    )
    sender = RecordingEmailSender()
    service = _deliverer(db_session, sender)
    delivery_id = await service.claim(
        user.id,
        NotificationKind.STALE_APPLICATION,
        stale_key(foreign.id, last_activity_at),
        NOW,
    )
    assert delivery_id is not None

    await service.deliver([delivery_id], user.id, NOW)

    await _assert_nothing_sent_and_claim_gone(db_session, sender, delivery_id, user)


@pytest.mark.asyncio
async def test_a_send_job_mixing_another_users_delivery_only_touches_its_own(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    # B2 con una lista: la entrega ajena se ignora y sigue como estaba.
    sender = RecordingEmailSender()
    service = NotificationDeliveryService(
        db_session,
        email_sender=sender,
        composers={NotificationKind.REMINDER_DUE: FixedComposer()},
        identities=FakeIdentities(),
    )
    mine = await service.claim(
        user.id, NotificationKind.REMINDER_DUE, "reminder:a", NOW
    )
    theirs = await service.claim(
        other_user.id, NotificationKind.REMINDER_DUE, "reminder:b", NOW
    )
    assert mine is not None and theirs is not None

    await service.deliver([mine, theirs], user.id, NOW)

    assert [email.to for email in sender.sent] == [
        f"{user.supertokens_user_id}@example.com"
    ]
    other = await NotificationDeliveryRepository(db_session).get(theirs, other_user.id)
    assert other is not None
    await db_session.refresh(other)
    assert other.status == DeliveryStatus.CLAIMED
