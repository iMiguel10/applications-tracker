"""Aviso de recordatorio vencido (RF-80, segundo plano §3: B7). Sin core ni SMTP:
identidades falsas, `InMemoryJobQueue` y `RecordingEmailSender`.

"Ahora" es una fecha fija lejos del reloj real: el barrido recorre los
recordatorios de todos los usuarios, y así no ve los de otras pruebas.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import (
    DeliveryStatus,
    NotificationKind,
    reminder_due_key,
)
from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import InMemoryJobQueue
from app.models.reminder import Reminder
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.notifications import ReminderDueSweep, composers_for, sweep
from app.services.notifications.reminder_due import ReminderDueComposer
from tests.factories import make_application, make_company, make_reminder

NOW = datetime(2031, 3, 10, 9, 0, tzinfo=UTC)
KIND = NotificationKind.REMINDER_DUE
WEBSITE = "http://localhost:5173"


class FakeIdentities(IdentityRepository):
    def __init__(self, unverified: set[str] | None = None) -> None:
        self.unverified = unverified or set()
        self.verification_checks = 0

    async def is_email_verified(self, supertokens_user_id: str) -> bool:
        self.verification_checks += 1
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
    claimed = await ReminderDueSweep(
        session, queue, identities=identities or FakeIdentities()
    ).run(now)
    return claimed, queue


async def _due(session: AsyncSession, user: CurrentUser, **fields: object) -> Reminder:
    values: dict[str, object] = {"due_at": NOW - timedelta(minutes=5)} | fields
    return await make_reminder(session, user.id, **values)


async def _user(session: AsyncSession, user: CurrentUser) -> User:
    loaded = await UserRepository(session).get_by_id(user.id)
    assert loaded is not None
    return loaded


# --- Barrido -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_reminder_that_just_fell_due_is_claimed_and_its_send_queued(
    db_session: AsyncSession, user: CurrentUser
):
    reminder = await _due(db_session, user)

    claimed, queue = await _sweep(db_session)

    assert claimed == 1
    [job] = queue.jobs
    assert job.job == "send_notification"
    assert job.kwargs["user_id"] == str(user.id)
    delivery = await NotificationDeliveryRepository(db_session).get(
        uuid.UUID(str(job.kwargs["delivery_ids"])), user.id
    )
    assert delivery is not None
    assert delivery.dedupe_key == reminder_due_key(reminder.id)


@pytest.mark.asyncio
async def test_the_next_sweeps_do_not_claim_it_again(
    db_session: AsyncSession, user: CurrentUser
):
    await _due(db_session, user)
    await _sweep(db_session)

    claimed, queue = await _sweep(db_session, now=NOW + timedelta(minutes=1))

    assert claimed == 0
    assert queue.jobs == []


@pytest.mark.asyncio
async def test_old_reminders_do_not_flood_the_inbox_when_the_channel_starts(
    db_session: AsyncSession, user: CurrentUser
):
    # B7: el día que se activa el canal, solo se avisa de lo vencido en 24 h.
    await _due(db_session, user, due_at=NOW - timedelta(days=90))
    await _due(db_session, user, due_at=NOW - timedelta(hours=24))
    recent = await _due(db_session, user, due_at=NOW - timedelta(hours=23))

    claimed, _ = await _sweep(db_session)

    assert claimed == 1
    assert (
        await NotificationDeliveryRepository(db_session).claim(
            user.id, KIND, reminder_due_key(recent.id), NOW
        )
        is None
    )


@pytest.mark.asyncio
async def test_future_done_and_dismissed_reminders_are_not_notified(
    db_session: AsyncSession, user: CurrentUser
):
    await _due(db_session, user, due_at=NOW + timedelta(minutes=1))
    await _due(db_session, user, status="done")
    await _due(db_session, user, status="dismissed")

    claimed, _ = await _sweep(db_session)

    assert claimed == 0


@pytest.mark.asyncio
async def test_accounts_with_the_notification_off_are_skipped(
    db_session: AsyncSession, user: CurrentUser
):
    (await _user(db_session, user)).notify_reminder_due = False
    await _due(db_session, user)

    claimed, _ = await _sweep(db_session)

    assert claimed == 0


@pytest.mark.asyncio
async def test_unverified_accounts_do_not_even_claim(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    # Si verificara más tarde, no recibiría de golpe lo acumulado.
    await _due(db_session, user)
    await _due(db_session, user)
    await _due(db_session, other_user)
    identities = FakeIdentities(unverified={user.supertokens_user_id})

    claimed, queue = await _sweep(db_session, identities=identities)

    assert claimed == 1
    assert [job.kwargs["user_id"] for job in queue.jobs] == [str(other_user.id)]
    # Una pregunta al core por cuenta y pasada, no por recordatorio.
    assert identities.verification_checks == 2


@pytest.mark.asyncio
async def test_unverified_accounts_cannot_starve_the_rest(
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
):
    # Los candidatos se leen por páginas: una página llena de cuentas sin verificar
    # no deja fuera a las verificadas que vienen después.
    monkeypatch.setattr(sweep, "PAGE_SIZE", 2)
    for minutes in (30, 29, 28):
        await _due(db_session, user, due_at=NOW - timedelta(minutes=minutes))
    await _due(db_session, other_user, due_at=NOW - timedelta(minutes=1))

    claimed, queue = await _sweep(
        db_session, identities=FakeIdentities(unverified={user.supertokens_user_id})
    )

    assert claimed == 1
    assert queue.jobs[0].kwargs["user_id"] == str(other_user.id)


@pytest.mark.asyncio
async def test_a_pass_claims_at_most_the_batch_limit(
    db_session: AsyncSession, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(sweep, "SWEEP_MAX_CLAIMS", 2)
    for minutes in (3, 2, 1):
        await _due(db_session, user, due_at=NOW - timedelta(minutes=minutes))

    first, _ = await _sweep(db_session)
    second, _ = await _sweep(db_session, now=NOW + timedelta(minutes=1))

    assert (first, second) == (2, 1)


@pytest.mark.asyncio
async def test_a_failed_delivery_is_claimed_again_once_its_retry_is_due(
    db_session: AsyncSession, user: CurrentUser
):
    await _due(db_session, user)
    _, queue = await _sweep(db_session)
    delivery_id = uuid.UUID(str(queue.jobs[0].kwargs["delivery_ids"]))
    repository = NotificationDeliveryRepository(db_session)
    delivery = await repository.get(delivery_id, user.id)
    assert delivery is not None
    delivery.status = DeliveryStatus.FAILED
    delivery.next_attempt_at = NOW + timedelta(minutes=5)
    await repository.save(delivery)

    too_early, _ = await _sweep(db_session, now=NOW + timedelta(minutes=4))
    due, _ = await _sweep(db_session, now=NOW + timedelta(minutes=5))

    assert (too_early, due) == (0, 1)


@pytest.mark.asyncio
async def test_with_advance_notice_the_reminder_is_notified_before_it_falls_due(
    db_session: AsyncSession, user: CurrentUser
):
    # RF-80: con 24 h de antelación, avisa de lo que vence en las próximas 24 h.
    (await _user(db_session, user)).reminder_notice_hours = 24
    await _due(db_session, user, due_at=NOW + timedelta(hours=20))
    await _due(db_session, user, due_at=NOW + timedelta(hours=25))

    claimed, _ = await _sweep(db_session)
    later, _ = await _sweep(db_session, now=NOW + timedelta(hours=1, minutes=1))

    assert (claimed, later) == (1, 1)


@pytest.mark.asyncio
async def test_changing_the_notice_after_sending_does_not_send_again(
    db_session: AsyncSession, user: CurrentUser
):
    account = await _user(db_session, user)
    account.reminder_notice_hours = 24
    await _due(db_session, user, due_at=NOW + timedelta(hours=2))
    await _sweep(db_session)

    account.reminder_notice_hours = 0
    claimed, _ = await _sweep(db_session, now=NOW + timedelta(hours=2, minutes=1))

    assert claimed == 0


# --- Compositor ------------------------------------------------------------------


async def _compose(session: AsyncSession, user: CurrentUser, reminder: Reminder):
    delivery_id = await NotificationDeliveryRepository(session).claim(
        user.id, KIND, reminder_due_key(reminder.id), NOW
    )
    assert delivery_id is not None
    delivery = await NotificationDeliveryRepository(session).get(delivery_id, user.id)
    assert delivery is not None
    composer = ReminderDueComposer(session, website_domain=WEBSITE)
    return await composer.compose_one(
        delivery, await _user(session, user), f"{WEBSITE}/unsubscribe?token=t"
    )


@pytest.mark.asyncio
async def test_email_names_the_reminder_its_application_and_the_local_time(
    db_session: AsyncSession, user: CurrentUser
):
    account = await _user(db_session, user)
    account.timezone = "Europe/Madrid"
    company = await make_company(db_session, user.id, "Lumen Labs")
    application = await make_application(
        db_session, user.id, company, position_title="Frontend Engineer"
    )
    reminder = await _due(
        db_session,
        user,
        title="Enviar la prueba técnica",
        application_id=application.id,
        due_at=datetime(2031, 3, 10, 8, 0, tzinfo=UTC),
    )

    email = await _compose(db_session, user, reminder)

    assert email is not None
    assert email.subject == "Recordatorio vencido: Enviar la prueba técnica"
    # 08:00 UTC en marzo = 09:00 en Madrid (invierno, +1).
    assert "lunes, 10 de marzo de 2031, 09:00" in email.text
    assert "Frontend Engineer · Lumen Labs" in email.text
    assert f"{WEBSITE}/applications/{application.id}" in email.text
    assert f"{WEBSITE}/preferences" in email.html


@pytest.mark.asyncio
async def test_email_uses_the_account_language_and_links_loose_reminders_to_the_list(
    db_session: AsyncSession, user: CurrentUser
):
    (await _user(db_session, user)).language = "en"
    reminder = await _due(db_session, user, title="Call back")

    email = await _compose(db_session, user, reminder)

    assert email is not None
    assert email.subject == "Reminder due: Call back"
    assert f"{WEBSITE}/reminders" in email.text
    assert "(UTC)" in email.text  # la cuenta aún no tiene zona


@pytest.mark.asyncio
async def test_user_text_cannot_inject_html_or_headers(
    db_session: AsyncSession, user: CurrentUser
):
    reminder = await _due(db_session, user, title="<b>Hola</b>\nBcc: x@evil.test")

    email = await _compose(db_session, user, reminder)

    assert email is not None
    assert "\n" not in email.subject
    assert "<b>Hola</b>" not in email.html
    assert "&lt;b&gt;Hola&lt;/b&gt;" in email.html


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["done", "dismissed"])
async def test_nothing_to_say_once_the_reminder_is_no_longer_pending(
    db_session: AsyncSession, user: CurrentUser, status: str
):
    reminder = await _due(db_session, user, status=status)

    assert await _compose(db_session, user, reminder) is None


@pytest.mark.asyncio
async def test_nothing_to_say_if_the_notification_was_turned_off_meanwhile(
    db_session: AsyncSession, user: CurrentUser
):
    reminder = await _due(db_session, user)
    (await _user(db_session, user)).notify_reminder_due = False

    assert await _compose(db_session, user, reminder) is None


@pytest.mark.asyncio
async def test_an_advance_notice_says_it_is_coming_up_not_overdue(
    db_session: AsyncSession, user: CurrentUser
):
    reminder = await _due(
        db_session, user, title="Enviar la prueba", due_at=NOW + timedelta(hours=20)
    )

    email = await _compose(db_session, user, reminder)

    assert email is not None
    assert email.subject == "Recordatorio: Enviar la prueba"
    assert "vence pronto" in email.text
    assert "Vence:" in email.text


# --- De punta a punta ----------------------------------------------------------


@pytest.mark.asyncio
async def test_sweep_then_send_delivers_exactly_one_email(
    db_session: AsyncSession, user: CurrentUser
):
    await _due(db_session, user, title="Seguimiento")
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
            [uuid.UUID(str(job.kwargs["delivery_ids"]))],
            uuid.UUID(str(job.kwargs["user_id"])),
            NOW,
        )
    _, again = await _sweep(
        db_session, now=NOW + timedelta(minutes=1), identities=identities
    )

    assert [email.subject for email in sender.sent] == [
        "Recordatorio vencido: Seguimiento"
    ]
    assert sender.sent[0].to == f"{user.supertokens_user_id}@example.com"
    assert again.jobs == []
