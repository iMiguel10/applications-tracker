"""Aviso de solicitudes sin actividad (RF-83): un aviso por solicitud y periodo de
inactividad, agrupados en un email por usuario y pasada. Sin core ni SMTP.

"Ahora" es una fecha fija lejos del reloj real: el barrido recorre las solicitudes
de todos los usuarios, y así no ve las de otras pruebas.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import DeliveryStatus
from app.infra.email import EmailNotSentError
from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import InMemoryJobQueue
from app.models.application import Application
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.notifications import StaleApplicationSweep, composers_for
from tests.factories import make_application, make_company

NOW = datetime(2031, 3, 10, 9, 0, tzinfo=UTC)


class FakeIdentities(IdentityRepository):
    def __init__(self, unverified: set[str] | None = None) -> None:
        self.unverified = unverified or set()

    async def is_email_verified(self, supertokens_user_id: str) -> bool:
        return supertokens_user_id not in self.unverified

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return f"{supertokens_user_id}@example.com"


async def _sweep(
    session: AsyncSession,
    *,
    now: datetime = NOW,
    identities: FakeIdentities | None = None,
) -> tuple[int, InMemoryJobQueue]:
    queue = InMemoryJobQueue()
    claimed = await StaleApplicationSweep(
        session, queue, identities=identities or FakeIdentities()
    ).run(now)
    return claimed, queue


async def _application(
    session: AsyncSession,
    user: CurrentUser,
    *,
    idle_days: float = 20,
    position: str = "Backend Developer",
    **fields: object,
) -> Application:
    company = await make_company(session, user.id)
    values: dict[str, object] = {
        "position_title": position,
        "status": "applied",
        "last_activity_at": NOW - timedelta(days=idle_days),
    }
    return await make_application(session, user.id, company, **(values | fields))


async def _user(session: AsyncSession, user: CurrentUser) -> User:
    loaded = await UserRepository(session).get_by_id(user.id)
    assert loaded is not None
    # Para cuentas activas: los avisos de inactividad vienen desactivados (RF-84).
    loaded.notify_stale = True
    return loaded


async def _send(
    session: AsyncSession,
    queue: InMemoryJobQueue,
    sender: RecordingEmailSender,
    now: datetime = NOW,
) -> None:
    identities = FakeIdentities()
    service = NotificationDeliveryService(
        session,
        email_sender=sender,
        composers=composers_for(session),
        identities=identities,
    )
    for job in queue.jobs:
        await service.deliver(
            [uuid.UUID(i) for i in str(job.kwargs["delivery_ids"]).split(",")],
            uuid.UUID(str(job.kwargs["user_id"])),
            now,
        )


# --- Barrido -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_stale_applications_of_a_user_go_in_one_email(
    db_session: AsyncSession, user: CurrentUser
):
    # El primer barrido encuentra todas las paradas de golpe: un email, no tres.
    await _user(db_session, user)
    for position in ("Uno", "Dos", "Tres"):
        await _application(db_session, user, position=position)
    sender = RecordingEmailSender()

    claimed, queue = await _sweep(db_session)
    await _send(db_session, queue, sender)
    again, _ = await _sweep(db_session, now=NOW + timedelta(hours=1))

    assert (claimed, len(queue.jobs), again) == (3, 1, 0)
    [email] = sender.sent
    assert email.subject == "3 solicitudes sin actividad"
    assert all(position in email.text for position in ("Uno", "Dos", "Tres"))


@pytest.mark.asyncio
async def test_each_user_gets_their_own_email(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await _user(db_session, user)
    await _user(db_session, other_user)
    await _application(db_session, user)
    await _application(db_session, other_user)

    _, queue = await _sweep(db_session)

    assert sorted(str(job.kwargs["user_id"]) for job in queue.jobs) == sorted(
        [str(user.id), str(other_user.id)]
    )


@pytest.mark.asyncio
async def test_the_account_threshold_decides_when_it_is_stale(
    db_session: AsyncSession, user: CurrentUser
):
    # RF-64: 14 días por defecto; con 7, una parada 10 días ya cuenta.
    await _user(db_session, user)
    await _application(db_session, user, idle_days=10)

    default, _ = await _sweep(db_session)
    (await _user(db_session, user)).stale_after_days = 7
    lower, _ = await _sweep(db_session)

    assert (default, lower) == (0, 1)


@pytest.mark.asyncio
async def test_it_notifies_again_only_after_moving_and_stalling_again(
    db_session: AsyncSession, user: CurrentUser
):
    # Un aviso por periodo de inactividad: la clave lleva la última actividad.
    await _user(db_session, user)
    application = await _application(db_session, user, idle_days=20)
    await _sweep(db_session)

    application.last_activity_at = NOW + timedelta(days=1)
    await db_session.flush()
    moving, _ = await _sweep(db_session, now=NOW + timedelta(days=2))
    stalled_again, _ = await _sweep(db_session, now=NOW + timedelta(days=16))

    assert (moving, stalled_again) == (0, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fields",
    [
        {"status": "saved"},
        {"status": "rejected"},
        {"status": "accepted"},
        {"archived_at": NOW - timedelta(days=1)},
    ],
    ids=["saved", "rejected", "accepted", "archived"],
)
async def test_only_active_applications_waiting_for_an_answer_count(
    db_session: AsyncSession, user: CurrentUser, fields: dict[str, Any]
):
    # Los mismos criterios que el bloque "Sin actividad" del dashboard (RF-64).
    await _user(db_session, user)
    await _application(db_session, user, **fields)

    claimed, _ = await _sweep(db_session)

    assert claimed == 0


@pytest.mark.asyncio
async def test_off_by_default_and_skipped_without_verification(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await _application(db_session, user)  # notify_stale apagado por defecto
    await _user(db_session, other_user)
    await _application(db_session, other_user)

    claimed, _ = await _sweep(
        db_session,
        identities=FakeIdentities(unverified={other_user.supertokens_user_id}),
    )

    assert claimed == 0


# --- Compositor ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_single_application_names_it_in_the_subject(
    db_session: AsyncSession, user: CurrentUser
):
    account = await _user(db_session, user)
    account.timezone = "Europe/Madrid"
    application = await _application(
        db_session, user, position="Frontend Engineer", idle_days=20, status="screening"
    )
    sender = RecordingEmailSender()

    _, queue = await _sweep(db_session)
    await _send(db_session, queue, sender)

    [email] = sender.sent
    assert email.subject.startswith("Solicitud sin actividad: Frontend Engineer en ")
    assert "(En revisión)" in email.text
    assert "desde el 18 de febrero de 2031, hace 20 días" in email.text
    assert f"/applications/{application.id}" in email.text
    assert "List-Unsubscribe" in email.headers


@pytest.mark.asyncio
async def test_english_email_with_plural_subject(
    db_session: AsyncSession, user: CurrentUser
):
    (await _user(db_session, user)).language = "en"
    await _application(db_session, user)
    await _application(db_session, user)
    sender = RecordingEmailSender()

    _, queue = await _sweep(db_session)
    await _send(db_session, queue, sender)

    [email] = sender.sent
    assert email.subject == "2 applications without activity"
    assert "(Applied): no activity since" in email.text


@pytest.mark.asyncio
async def test_applications_that_moved_meanwhile_leave_the_list(
    db_session: AsyncSession, user: CurrentUser
):
    await _user(db_session, user)
    await _application(db_session, user, position="Sigue parada")
    moved = await _application(db_session, user, position="Se movió")
    sender = RecordingEmailSender()
    _, queue = await _sweep(db_session)

    moved.last_activity_at = NOW
    await db_session.flush()
    await _send(db_session, queue, sender)

    [email] = sender.sent
    assert "Sigue parada" in email.text
    assert "Se movió" not in email.text
    assert email.subject.startswith("Solicitud sin actividad: Sigue parada")
    # Su entrega se borra: si vuelve a pararse, es otro periodo y otro aviso.
    deliveries = NotificationDeliveryRepository(db_session)
    delivery_ids = [
        uuid.UUID(i) for i in str(queue.jobs[0].kwargs["delivery_ids"]).split(",")
    ]
    remaining = await deliveries.get_many(delivery_ids, user.id)
    assert [d.status for d in remaining] == [DeliveryStatus.SENT]


@pytest.mark.asyncio
async def test_nothing_is_sent_if_no_application_is_still_stale(
    db_session: AsyncSession, user: CurrentUser
):
    await _user(db_session, user)
    application = await _application(db_session, user)
    sender = RecordingEmailSender()
    _, queue = await _sweep(db_session)

    application.status = "rejected"
    await db_session.flush()
    await _send(db_session, queue, sender)

    assert sender.sent == []


@pytest.mark.asyncio
async def test_a_failed_send_marks_every_application_in_the_email(
    db_session: AsyncSession, user: CurrentUser
):
    # Un solo email: su resultado vale para todas las entregas que cubre.
    await _user(db_session, user)
    await _application(db_session, user)
    await _application(db_session, user)
    sender = RecordingEmailSender(fail_with=EmailNotSentError("sin conexión"))
    _, queue = await _sweep(db_session)

    await _send(db_session, queue, sender)

    delivery_ids = [
        uuid.UUID(i) for i in str(queue.jobs[0].kwargs["delivery_ids"]).split(",")
    ]
    deliveries = await NotificationDeliveryRepository(db_session).get_many(
        delivery_ids, user.id
    )
    for delivery in deliveries:
        await db_session.refresh(delivery)
    assert [d.status for d in deliveries] == [DeliveryStatus.FAILED] * 2
    retried, retry_queue = await _sweep(db_session, now=NOW + timedelta(hours=1))
    assert (retried, len(retry_queue.jobs)) == (2, 1)
