"""Resumen semanal (RF-82, segundo plano §6). Sin core ni SMTP.

Lunes 10 de marzo de 2031, 9:00 UTC: lejos del reloj real, para que el barrido no
vea datos de otras pruebas.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import InMemoryJobQueue
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.notifications import WeeklyDigestSweep, composers_for
from tests.factories import (
    make_application,
    make_company,
    make_interview,
    make_reminder,
)

MONDAY = datetime(2031, 3, 10, 9, 0, tzinfo=UTC)


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
    now: datetime = MONDAY,
    identities: FakeIdentities | None = None,
) -> tuple[int, InMemoryJobQueue]:
    queue = InMemoryJobQueue()
    claimed = await WeeklyDigestSweep(
        session, queue, identities=identities or FakeIdentities()
    ).run(now)
    return claimed, queue


async def _subscriber(
    session: AsyncSession, user: CurrentUser, **fields: object
) -> User:
    loaded = await UserRepository(session).get_by_id(user.id)
    assert loaded is not None
    loaded.notify_weekly_digest = True  # desactivado por defecto (RF-84)
    for name, value in fields.items():
        setattr(loaded, name, value)
    await session.flush()
    return loaded


async def _digest(
    session: AsyncSession, now: datetime = MONDAY
) -> list[RecordingEmailSender]:
    """Barre y envía; devuelve el emisor con lo enviado."""
    identities = FakeIdentities()
    sender = RecordingEmailSender()
    _, queue = await _sweep(session, now=now, identities=identities)
    service = NotificationDeliveryService(
        session,
        email_sender=sender,
        composers=composers_for(session),
        identities=identities,
    )
    for job in queue.jobs:
        await service.deliver(
            [uuid.UUID(str(job.kwargs["delivery_ids"]))],
            uuid.UUID(str(job.kwargs["user_id"])),
            now,
        )
    return [sender]


# --- Barrido -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_monday_morning_claims_once_for_the_whole_week(
    db_session: AsyncSession, user: CurrentUser
):
    await _subscriber(db_session, user)

    first, _ = await _sweep(db_session)
    later_that_day, _ = await _sweep(db_session, now=MONDAY + timedelta(hours=5))
    next_week, _ = await _sweep(db_session, now=MONDAY + timedelta(days=7))

    assert (first, later_that_day, next_week) == (1, 0, 1)


@pytest.mark.asyncio
async def test_each_user_gets_it_at_eight_in_their_own_zone(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    # B9 en el barrido: a las 9:00 UTC ya son las 10:00 en Madrid, pero en Nueva
    # York (−4 desde el domingo) aún son las 5:00.
    await _subscriber(db_session, user, timezone="Europe/Madrid")
    await _subscriber(db_session, other_user, timezone="America/New_York")

    _, at_nine = await _sweep(db_session)
    _, at_noon = await _sweep(db_session, now=MONDAY.replace(hour=12))

    assert [job.kwargs["user_id"] for job in at_nine.jobs] == [str(user.id)]
    assert [job.kwargs["user_id"] for job in at_noon.jobs] == [str(other_user.id)]


@pytest.mark.asyncio
async def test_off_by_default_and_skipped_without_verification(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await _subscriber(db_session, other_user)

    claimed, _ = await _sweep(
        db_session,
        identities=FakeIdentities(unverified={other_user.supertokens_user_id}),
    )

    assert claimed == 0


# --- Contenido -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_digest_has_what_the_dashboard_has(
    db_session: AsyncSession, user: CurrentUser
):
    await _subscriber(db_session, user, timezone="Europe/Madrid")
    company = await make_company(db_session, user.id, "Lumen Labs")
    active = await make_application(
        db_session,
        user.id,
        company,
        position_title="Frontend Engineer",
        status="interviewing",
        last_activity_at=MONDAY,
    )
    await make_interview(
        db_session,
        active,
        scheduled_at=MONDAY + timedelta(days=2),
        interview_type="technical",
    )
    await make_interview(db_session, active, scheduled_at=MONDAY + timedelta(days=9))
    await make_reminder(
        db_session, user.id, title="Llamar a Lumen", due_at=MONDAY - timedelta(days=1)
    )
    await make_reminder(
        db_session,
        user.id,
        title="Preparar la prueba",
        due_at=MONDAY + timedelta(days=3),
    )
    await make_reminder(
        db_session,
        user.id,
        title="Dentro de un mes",
        due_at=MONDAY + timedelta(days=30),
    )
    await make_application(
        db_session,
        user.id,
        await make_company(db_session, user.id, "Globex"),
        position_title="Data Engineer",
        status="applied",
        last_activity_at=MONDAY - timedelta(days=20),
    )

    [sender] = await _digest(db_session)

    [email] = sender.sent
    text = email.text
    assert email.subject == "Tu resumen semanal: semana del 10 de marzo de 2031"
    assert "Enviada: 1" in text and "Entrevistas: 1" in text
    # Solo la entrevista de esta semana, a la hora de Madrid.
    assert "miércoles, 12 de marzo de 2031, 10:00: entrevista técnica" in text
    assert text.count("Frontend Engineer en Lumen Labs") == 1
    assert "Vencido: Llamar a Lumen" in text
    assert "- Preparar la prueba" in text
    assert "Dentro de un mes" not in text
    assert "Data Engineer en Globex: 20 días" in text
    assert "List-Unsubscribe" in email.headers


@pytest.mark.asyncio
async def test_an_empty_week_still_gets_its_digest(
    db_session: AsyncSession, user: CurrentUser
):
    # Quien lo activó espera recibirlo cada lunes, aunque no haya nada.
    await _subscriber(db_session, user, language="en")

    [sender] = await _digest(db_session)

    [email] = sender.sent
    assert email.subject == "Your weekly summary: week of March 10, 2031"
    assert "All caught up!" in email.text


@pytest.mark.asyncio
async def test_long_lists_are_cut_and_point_to_the_app(
    db_session: AsyncSession, user: CurrentUser
):
    await _subscriber(db_session, user)
    for day in range(12):
        await make_reminder(
            db_session,
            user.id,
            title=f"R{day}",
            due_at=MONDAY - timedelta(days=day + 1),
        )

    [sender] = await _digest(db_session)

    [email] = sender.sent
    assert email.text.count("Vencido:") == 10
    assert "Y 2 más en" in email.text
