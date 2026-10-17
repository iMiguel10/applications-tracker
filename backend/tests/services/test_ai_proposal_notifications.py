"""Aviso por email de propuesta de IA terminada (RF-157, decisión 0021). Sin core
ni SMTP: identidades falsas, `InMemoryJobQueue` y `RecordingEmailSender`.

"Ahora" es una fecha fija lejos del reloj real: el barrido recorre las propuestas
de todos los usuarios, y así no ve las de otras pruebas.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications import NotificationKind, ai_proposal_key
from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import InMemoryJobQueue
from app.models.ai_proposal import AiProposal
from app.models.company import Company
from app.models.user import User
from app.repositories.ai_proposal_repository import AiProposalRepository
from app.repositories.identity_repository import IdentityRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import NotificationDeliveryService
from app.services.notifications import AiProposalFinishedSweep, composers_for
from app.services.notifications.ai_proposal_finished import AiProposalFinishedComposer
from tests.factories import make_ai_proposal, make_application, make_company

NOW = datetime(2031, 3, 10, 9, 0, tzinfo=UTC)
KIND = NotificationKind.AI_PROPOSAL_FINISHED
WEBSITE = "http://localhost:5173"
SECRET_BULLET = "Logro privado que nunca debe salir en un email"


class FakeIdentities(IdentityRepository):
    def __init__(self, unverified: set[str] | None = None) -> None:
        self.unverified = unverified or set()

    async def is_email_verified(self, supertokens_user_id: str) -> bool:
        return supertokens_user_id not in self.unverified

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return f"{supertokens_user_id}@example.com"


async def _user(session: AsyncSession, user: CurrentUser) -> User:
    loaded = await UserRepository(session).get_by_id(user.id)
    assert loaded is not None
    return loaded


async def _notify_on(session: AsyncSession, user: CurrentUser) -> User:
    account = await _user(session, user)
    account.notify_ai_proposal = True
    await session.flush()
    return account


async def _finished(
    session: AsyncSession,
    user: CurrentUser,
    *,
    position: str = "Backend Developer",
    company: str = "Acme",
    **fields: Any,
) -> AiProposal:
    """Una propuesta terminada bien hace 5 minutos, salvo que se diga otra cosa."""
    # La misma empresa para todas las de la prueba: el nombre es único por cuenta.
    existing = await session.scalar(
        select(Company).where(Company.user_id == user.id, Company.name == company)
    )
    application = await make_application(
        session,
        user.id,
        existing or await make_company(session, user.id, company),
        position_title=position,
    )
    values: dict[str, Any] = {
        "status": "succeeded",
        "proposal": {"summary": SECRET_BULLET},
        "finished_at": NOW - timedelta(minutes=5),
    } | fields
    if values["status"] != "succeeded":
        values["proposal"] = None
    return await make_ai_proposal(session, application, **values)


async def _sweep(
    session: AsyncSession,
    *,
    now: datetime = NOW,
    identities: FakeIdentities | None = None,
) -> tuple[int, InMemoryJobQueue]:
    queue = InMemoryJobQueue()
    claimed = await AiProposalFinishedSweep(
        session, queue, identities=identities or FakeIdentities()
    ).run(now)
    return claimed, queue


# --- Barrido -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_proposal_that_just_finished_is_claimed_and_its_send_queued(
    db_session: AsyncSession, user: CurrentUser
):
    await _notify_on(db_session, user)
    proposal = await _finished(db_session, user)

    claimed, queue = await _sweep(db_session)

    assert claimed == 1
    [job] = queue.jobs
    assert job.job == "send_notification"
    delivery = await NotificationDeliveryRepository(db_session).get(
        uuid.UUID(str(job.kwargs["delivery_ids"])), user.id
    )
    assert delivery is not None
    assert delivery.kind == KIND
    assert delivery.dedupe_key == ai_proposal_key(proposal.id)


@pytest.mark.asyncio
async def test_off_by_default(db_session: AsyncSession, user: CurrentUser):
    # 0021: casi siempre se espera en la página; el email hay que pedirlo.
    assert (await _user(db_session, user)).notify_ai_proposal is False
    await _finished(db_session, user)

    claimed, queue = await _sweep(db_session)

    assert claimed == 0
    assert queue.jobs == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_code"),
    [
        ("invalid", "ai_response_invalid"),
        ("failed", "ai_provider_unavailable"),
        ("rejected", "ai_offer_insufficient"),
    ],
)
async def test_unsuccessful_proposals_are_notified_too(
    db_session: AsyncSession, user: CurrentUser, status: str, error_code: str
):
    await _notify_on(db_session, user)
    await _finished(db_session, user, status=status, error_code=error_code)

    claimed, _ = await _sweep(db_session)

    assert claimed == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["queued", "running"])
async def test_proposals_in_flight_are_not_notified(
    db_session: AsyncSession, user: CurrentUser, status: str
):
    await _notify_on(db_session, user)
    await _finished(db_session, user, status=status, finished_at=None)

    claimed, _ = await _sweep(db_session)

    assert claimed == 0


@pytest.mark.asyncio
async def test_turning_it_on_does_not_send_old_proposals(
    db_session: AsyncSession, user: CurrentUser
):
    # Solo la última hora; y las anteriores a este aviso no tienen finished_at.
    await _notify_on(db_session, user)
    await _finished(db_session, user, finished_at=NOW - timedelta(hours=1))
    await _finished(db_session, user, finished_at=None)
    recent = await _finished(db_session, user, finished_at=NOW - timedelta(minutes=59))

    claimed, queue = await _sweep(db_session)

    assert claimed == 1
    delivery = await NotificationDeliveryRepository(db_session).get(
        uuid.UUID(str(queue.jobs[0].kwargs["delivery_ids"])), user.id
    )
    assert delivery is not None
    assert delivery.dedupe_key == ai_proposal_key(recent.id)


@pytest.mark.asyncio
async def test_unverified_accounts_do_not_claim(
    db_session: AsyncSession, user: CurrentUser
):
    await _notify_on(db_session, user)
    await _finished(db_session, user)

    claimed, _ = await _sweep(
        db_session, identities=FakeIdentities(unverified={user.supertokens_user_id})
    )

    assert claimed == 0


@pytest.mark.asyncio
async def test_the_next_sweeps_do_not_claim_it_again(
    db_session: AsyncSession, user: CurrentUser
):
    await _notify_on(db_session, user)
    await _finished(db_session, user)
    await _sweep(db_session)

    claimed, queue = await _sweep(db_session, now=NOW + timedelta(minutes=1))

    assert claimed == 0
    assert queue.jobs == []


@pytest.mark.asyncio
async def test_finishing_marks_finished_at(db_session: AsyncSession, user: CurrentUser):
    # El cierre del worker (finish) fecha la propuesta: sin eso, nunca se avisaría.

    application = await make_application(db_session, user.id)
    proposal = await make_ai_proposal(db_session, application, status="running")

    updated = await AiProposalRepository(db_session).finish(
        user.id,
        proposal.id,
        {"status": "failed", "error_code": "ai_provider_unavailable"},
    )
    await db_session.refresh(proposal)

    assert updated is True
    assert proposal.finished_at is not None


# --- Email ---------------------------------------------------------------------


async def _compose(session: AsyncSession, user: CurrentUser, proposal: AiProposal):
    delivery_id = await NotificationDeliveryRepository(session).claim(
        user.id, KIND, ai_proposal_key(proposal.id), NOW
    )
    assert delivery_id is not None
    delivery = await NotificationDeliveryRepository(session).get(delivery_id, user.id)
    assert delivery is not None
    composer = AiProposalFinishedComposer(session, website_domain=WEBSITE)
    return await composer.compose_one(
        delivery, await _user(session, user), f"{WEBSITE}/unsubscribe?token=t"
    )


@pytest.mark.asyncio
async def test_a_ready_cv_links_to_its_review_and_never_carries_its_content(
    db_session: AsyncSession, user: CurrentUser
):
    await _notify_on(db_session, user)
    proposal = await _finished(db_session, user)

    email = await _compose(db_session, user, proposal)

    assert email is not None
    assert email.subject == "Tu CV adaptado para Backend Developer en Acme está listo"
    review = f"{WEBSITE}/applications/{proposal.application_id}/ai/{proposal.id}"
    assert review in email.text
    assert review in email.html
    assert "Revisar la propuesta" in email.html
    assert f"{WEBSITE}/unsubscribe?token=t" in email.text
    # Son datos del perfil: el email solo lleva el enlace.
    assert SECRET_BULLET not in email.text
    assert SECRET_BULLET not in email.html


@pytest.mark.asyncio
async def test_a_failed_letter_says_why_and_links_to_the_application(
    db_session: AsyncSession, user: CurrentUser
):
    await _notify_on(db_session, user)
    proposal = await _finished(
        db_session,
        user,
        kind="cover_letter",
        status="failed",
        error_code="ai_provider_unavailable",
    )

    email = await _compose(db_session, user, proposal)

    assert email is not None
    assert (
        email.subject == "No se pudo escribir tu carta para Backend Developer en Acme"
    )
    assert "No se pudo contactar con el proveedor de IA." in email.text
    assert "No se pudo contactar con el proveedor de IA." in email.html
    assert f"{WEBSITE}/applications/{proposal.application_id}\n" in email.text
    assert "/ai/" not in email.text


@pytest.mark.asyncio
async def test_the_email_uses_the_account_language(
    db_session: AsyncSession, user: CurrentUser
):
    account = await _notify_on(db_session, user)
    account.language = "en"
    proposal = await _finished(
        db_session, user, status="invalid", error_code="ai_response_invalid"
    )

    email = await _compose(db_session, user, proposal)

    assert email is not None
    assert email.subject == "Your CV for Backend Developer at Acme couldn't be tailored"
    assert "did not pass the check" in email.text
    assert "Open the application" in email.html


@pytest.mark.asyncio
async def test_user_text_cannot_inject_html_or_headers(
    db_session: AsyncSession, user: CurrentUser
):
    await _notify_on(db_session, user)
    proposal = await _finished(
        db_session, user, position="<b>Dev</b>\nBcc: x@evil.test", company="Acme"
    )

    email = await _compose(db_session, user, proposal)

    assert email is not None
    assert "\n" not in email.subject
    assert "<b>Dev</b>" not in email.html
    assert "&lt;b&gt;Dev&lt;/b&gt;" in email.html


@pytest.mark.asyncio
async def test_nothing_to_say_if_the_notification_was_turned_off_meanwhile(
    db_session: AsyncSession, user: CurrentUser
):
    account = await _notify_on(db_session, user)
    proposal = await _finished(db_session, user)
    account.notify_ai_proposal = False

    assert await _compose(db_session, user, proposal) is None


# --- De punta a punta ----------------------------------------------------------


@pytest.mark.asyncio
async def test_sweep_then_send_delivers_exactly_one_email(
    db_session: AsyncSession, user: CurrentUser
):
    await _notify_on(db_session, user)
    await _finished(db_session, user)
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
        "Tu CV adaptado para Backend Developer en Acme está listo"
    ]
    assert sender.sent[0].to == f"{user.supertokens_user_id}@example.com"
    assert again.jobs == []
