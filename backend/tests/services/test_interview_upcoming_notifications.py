"""Aviso de entrevista próxima (RF-81, segundo plano §4: B8). Sin core ni SMTP.

"Ahora" es una fecha fija lejos del reloj real: el barrido recorre las entrevistas
de todos los usuarios, y así no ve las de otras pruebas.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import NotificationKind, interview_key
from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import InMemoryJobQueue
from app.models.interview import Interview
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.notifications import InterviewUpcomingSweep, composers_for
from app.services.notifications.interview_upcoming import InterviewUpcomingComposer
from tests.factories import make_application, make_company, make_interview

NOW = datetime(2031, 3, 10, 9, 0, tzinfo=UTC)
KIND = NotificationKind.INTERVIEW_UPCOMING
WEBSITE = "http://localhost:5173"


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
    claimed = await InterviewUpcomingSweep(
        session, queue, identities=identities or FakeIdentities()
    ).run(now)
    return claimed, queue


async def _interview(
    session: AsyncSession, user: CurrentUser, *, in_hours: float = 20, **fields: object
) -> Interview:
    company = await make_company(session, user.id, f"Lumen Labs {uuid.uuid4().hex[:4]}")
    application = await make_application(
        session, user.id, company, position_title="Frontend Engineer"
    )
    values: dict[str, object] = {"scheduled_at": NOW + timedelta(hours=in_hours)}
    return await make_interview(session, application, **(values | fields))


async def _user(session: AsyncSession, user: CurrentUser) -> User:
    loaded = await UserRepository(session).get_by_id(user.id)
    assert loaded is not None
    return loaded


# --- Barrido -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_interview_within_the_notice_is_claimed_once(
    db_session: AsyncSession, user: CurrentUser
):
    # 24 h de antelación por defecto: la de dentro de 20 h ya toca.
    interview = await _interview(db_session, user, in_hours=20)

    claimed, queue = await _sweep(db_session)
    again, _ = await _sweep(db_session, now=NOW + timedelta(minutes=5))

    assert (claimed, again) == (1, 0)
    delivery = await NotificationDeliveryRepository(db_session).get(
        uuid.UUID(str(queue.jobs[0].kwargs["delivery_id"])), user.id
    )
    assert delivery is not None
    assert delivery.dedupe_key == interview_key(interview.id, interview.scheduled_at)


@pytest.mark.asyncio
async def test_an_interview_beyond_the_notice_waits(
    db_session: AsyncSession, user: CurrentUser
):
    await _interview(db_session, user, in_hours=30)

    now_claimed, _ = await _sweep(db_session)
    later_claimed, _ = await _sweep(db_session, now=NOW + timedelta(hours=6))

    assert (now_claimed, later_claimed) == (0, 1)


@pytest.mark.asyncio
async def test_the_account_notice_is_respected(
    db_session: AsyncSession, user: CurrentUser
):
    (await _user(db_session, user)).interview_notice_hours = 2
    await _interview(db_session, user, in_hours=3)

    early, _ = await _sweep(db_session)
    on_time, _ = await _sweep(db_session, now=NOW + timedelta(hours=1, minutes=5))

    assert (early, on_time) == (0, 1)


@pytest.mark.asyncio
async def test_moving_the_interview_notifies_again_and_not_moving_it_does_not(
    db_session: AsyncSession, user: CurrentUser
):
    # B8: la clave lleva la hora.
    interview = await _interview(db_session, user, in_hours=20)
    await _sweep(db_session)

    same, _ = await _sweep(db_session, now=NOW + timedelta(hours=1))
    interview.scheduled_at = NOW + timedelta(hours=22)
    await db_session.flush()
    moved, _ = await _sweep(db_session, now=NOW + timedelta(hours=1, minutes=5))

    assert (same, moved) == (0, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("in_hours", "outcome"),
    [(-1, "pending"), (10, "passed"), (10, "failed"), (10, "cancelled")],
    ids=["already_started", "passed", "failed", "cancelled"],
)
async def test_started_or_decided_interviews_are_not_notified(
    db_session: AsyncSession, user: CurrentUser, in_hours: float, outcome: str
):
    await _interview(db_session, user, in_hours=in_hours, outcome=outcome)

    claimed, _ = await _sweep(db_session)

    assert claimed == 0


@pytest.mark.asyncio
async def test_accounts_with_the_notification_off_or_unverified_are_skipped(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    (await _user(db_session, user)).notify_interview = False
    await _interview(db_session, user)
    await _interview(db_session, other_user)

    claimed, _ = await _sweep(
        db_session,
        identities=FakeIdentities(unverified={other_user.supertokens_user_id}),
    )

    assert claimed == 0


# --- Compositor ------------------------------------------------------------------


async def _compose(session: AsyncSession, user: CurrentUser, interview: Interview):
    repository = NotificationDeliveryRepository(session)
    delivery_id = await repository.claim(
        user.id, KIND, interview_key(interview.id, interview.scheduled_at), NOW
    )
    assert delivery_id is not None
    delivery = await repository.get(delivery_id, user.id)
    assert delivery is not None
    composer = InterviewUpcomingComposer(session, website_domain=WEBSITE)
    return await composer.compose(
        delivery, await _user(session, user), f"{WEBSITE}/unsubscribe?token=t"
    )


@pytest.mark.asyncio
async def test_email_says_when_with_whom_and_how_in_the_users_zone(
    db_session: AsyncSession, user: CurrentUser
):
    (await _user(db_session, user)).timezone = "Europe/Madrid"
    interview = await _interview(
        db_session,
        user,
        scheduled_at=datetime(2031, 3, 11, 8, 30, tzinfo=UTC),
        interview_type="technical",
        format="online",
        duration_minutes=45,
        interviewers="Ana López",
    )

    email = await _compose(db_session, user, interview)

    assert email is not None
    assert email.subject.startswith("Entrevista: Frontend Engineer en Lumen Labs")
    assert "entrevista técnica para Frontend Engineer" in email.text
    assert "martes, 11 de marzo de 2031, 09:30" in email.text
    assert "Duración: 45 minutos" in email.text
    # Los mismos nombres que la interfaz.
    assert "Formato: Online" in email.text
    assert "Con: Ana López" in email.html
    assert f"{WEBSITE}/applications/{interview.application_id}" in email.text
    assert f"{WEBSITE}/unsubscribe?token=t" in email.html


@pytest.mark.asyncio
async def test_email_in_english_without_optional_details(
    db_session: AsyncSession, user: CurrentUser
):
    (await _user(db_session, user)).language = "en"
    interview = await _interview(db_session, user)

    email = await _compose(db_session, user, interview)

    assert email is not None
    assert email.subject.startswith("Interview: Frontend Engineer at Lumen Labs")
    assert "You have an interview for Frontend Engineer" in email.text
    assert "Duration" not in email.text


@pytest.mark.asyncio
async def test_nothing_to_say_if_it_was_moved_or_decided_meanwhile(
    db_session: AsyncSession, user: CurrentUser
):
    moved = await _interview(db_session, user)
    decided = await _interview(db_session, user)
    repository = NotificationDeliveryRepository(db_session)
    deliveries = []
    for interview in (moved, decided):
        delivery_id = await repository.claim(
            user.id, KIND, interview_key(interview.id, interview.scheduled_at), NOW
        )
        assert delivery_id is not None
        deliveries.append(await repository.get(delivery_id, user.id))

    moved.scheduled_at += timedelta(hours=1)
    decided.outcome = "cancelled"
    await db_session.flush()

    composer = InterviewUpcomingComposer(db_session, website_domain=WEBSITE)
    account = await _user(db_session, user)
    for delivery in deliveries:
        assert delivery is not None
        assert await composer.compose(delivery, account, "x") is None


# --- De punta a punta ----------------------------------------------------------


@pytest.mark.asyncio
async def test_sweep_then_send_delivers_exactly_one_email(
    db_session: AsyncSession, user: CurrentUser
):
    await _interview(db_session, user)
    identities = FakeIdentities()
    sender = RecordingEmailSender()
    _, queue = await _sweep(db_session, identities=identities)
    delivery = NotificationDeliveryService(
        db_session,
        email_sender=sender,
        composers=composers_for(db_session),
        identities=identities,
    )

    for job in queue.jobs:
        await delivery.deliver(
            uuid.UUID(str(job.kwargs["delivery_id"])),
            uuid.UUID(str(job.kwargs["user_id"])),
            NOW,
        )
    _, again = await _sweep(
        db_session, now=NOW + timedelta(minutes=5), identities=identities
    )

    [email] = sender.sent
    assert email.subject.startswith("Entrevista: Frontend Engineer en Lumen Labs")
    assert "List-Unsubscribe" in email.headers
    assert again.jobs == []
