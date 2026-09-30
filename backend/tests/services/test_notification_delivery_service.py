"""Envío de una entrega de aviso: "nunca dos veces" (RF-87, segundo plano §4:
B2, B4, B5). Sin core ni SMTP: identidades falsas y `RecordingEmailSender`."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.notifications import (
    MAX_DELIVERY_ATTEMPTS,
    DeliveryStatus,
    NotificationKind,
)
from app.domain.unsubscribe import verify_unsubscribe_token
from app.infra.email import EmailDeliveryUnknownError, EmailNotSentError
from app.infra.email.recording import RecordingEmailSender
from app.infra.email.templates import RenderedEmail
from app.infra.queue import InMemoryJobQueue, JobArg, QueueUnavailableError
from app.jobs.notifications import notification_cron_jobs
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.repositories.notification_delivery_repository import (
    NotificationDeliveryRepository,
)
from app.schemas.user import CurrentUser
from app.services.notification_delivery_service import (
    SEND_NOTIFICATION,
    NotificationDeliveryService,
    SingleDeliveryComposer,
)

NOW = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)
KIND = NotificationKind.REMINDER_DUE
EMAIL = "persona@example.com"


class FakeIdentities(IdentityRepository):
    def __init__(self, email: str | None = EMAIL) -> None:
        self.email = email

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return self.email


class FakeComposer(SingleDeliveryComposer):
    def __init__(self, *, reason_gone: bool = False) -> None:
        self.reason_gone = reason_gone
        self.composed: list[str] = []
        self.unsubscribe_links: list[str] = []

    async def compose_one(
        self, delivery: NotificationDelivery, user: User, unsubscribe_link: str
    ) -> RenderedEmail | None:
        self.composed.append(delivery.dedupe_key)
        self.unsubscribe_links.append(unsubscribe_link)
        if self.reason_gone:
            return None
        return RenderedEmail(subject="Aviso", text="Texto", html="<p>Texto</p>")


def _service(
    session: AsyncSession,
    sender: RecordingEmailSender,
    *,
    composer: FakeComposer | None = None,
    email: str | None = EMAIL,
) -> NotificationDeliveryService:
    return NotificationDeliveryService(
        session,
        email_sender=sender,
        composers={KIND: composer or FakeComposer()},
        identities=FakeIdentities(email),
    )


async def _delivery(
    session: AsyncSession, delivery_id: uuid.UUID, user: CurrentUser
) -> NotificationDelivery:
    delivery = await NotificationDeliveryRepository(session).get(delivery_id, user.id)
    assert delivery is not None
    await session.refresh(delivery)
    return delivery


async def _claim(service: NotificationDeliveryService, user: CurrentUser) -> uuid.UUID:
    delivery_id = await service.claim(user.id, KIND, "reminder:1", NOW)
    assert delivery_id is not None
    return delivery_id


@pytest.mark.asyncio
async def test_accepted_email_is_sent_once(db_session: AsyncSession, user: CurrentUser):
    sender = RecordingEmailSender()
    service = _service(db_session, sender)
    delivery_id = await _claim(service, user)

    await service.deliver([delivery_id], user.id, NOW)
    # Encolado dos veces, o un worker que lo toma por abandonado al arrancar.
    await service.deliver([delivery_id], user.id, NOW)

    delivery = await _delivery(db_session, delivery_id, user)
    assert delivery.status == DeliveryStatus.SENT
    assert delivery.sent_at == NOW
    assert [email.to for email in sender.sent] == [EMAIL]


@pytest.mark.asyncio
async def test_every_email_carries_its_one_click_unsubscribe(
    db_session: AsyncSession, user: CurrentUser
):
    # RF-85: la cabecera para el botón del cliente de correo (RFC 8058) y el enlace
    # a la página que pide confirmar, con un token de ese usuario y ese tipo.
    sender = RecordingEmailSender()
    composer = FakeComposer()
    service = _service(db_session, sender, composer=composer)
    delivery_id = await _claim(service, user)

    await service.deliver([delivery_id], user.id, NOW)

    [email] = sender.sent
    one_click = email.headers["List-Unsubscribe"]
    assert one_click.startswith(f"<{settings.api_domain.rstrip('/')}/api/v1/")
    assert email.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    [link] = composer.unsubscribe_links
    assert link.startswith(f"{settings.website_domain.rstrip('/')}/unsubscribe?token=")
    token = link.split("token=")[1]
    assert f"token={token}>" in one_click
    assert verify_unsubscribe_token(token, settings.app_secret) == (user.id, KIND)


@pytest.mark.asyncio
async def test_ambiguous_failure_is_unknown_and_never_retried(
    db_session: AsyncSession, user: CurrentUser
):
    # B4: el servidor pudo aceptarlo; reintentar podría duplicarlo.
    sender = RecordingEmailSender(fail_with=EmailDeliveryUnknownError("corte"))
    service = _service(db_session, sender)
    delivery_id = await _claim(service, user)

    await service.deliver([delivery_id], user.id, NOW)

    delivery = await _delivery(db_session, delivery_id, user)
    assert delivery.status == DeliveryStatus.UNKNOWN
    assert delivery.next_attempt_at is None
    assert (
        await service.claim(user.id, KIND, "reminder:1", NOW + timedelta(days=1))
        is None
    )


@pytest.mark.asyncio
async def test_failure_before_delivery_is_retried_up_to_the_limit(
    db_session: AsyncSession, user: CurrentUser
):
    # B5: con seguridad no salió, así que se reintenta con espera creciente, y
    # tras el último intento se da por fallida.
    sender = RecordingEmailSender(fail_with=EmailNotSentError("sin conexión"))
    service = _service(db_session, sender)
    delivery_id = await _claim(service, user)
    now = NOW

    for attempt in range(1, MAX_DELIVERY_ATTEMPTS + 1):
        await service.deliver([delivery_id], user.id, now)
        delivery = await _delivery(db_session, delivery_id, user)
        assert delivery.status == DeliveryStatus.FAILED
        assert delivery.attempts == attempt
        if attempt == MAX_DELIVERY_ATTEMPTS:
            break
        assert delivery.next_attempt_at is not None
        assert await service.claim(user.id, KIND, "reminder:1", now) is None
        now = delivery.next_attempt_at
        assert await service.claim(user.id, KIND, "reminder:1", now) == delivery_id

    assert delivery.next_attempt_at is None
    assert (
        await service.claim(user.id, KIND, "reminder:1", now + timedelta(days=1))
        is None
    )


@pytest.mark.asyncio
async def test_retry_that_succeeds_ends_sent(
    db_session: AsyncSession, user: CurrentUser
):
    sender = RecordingEmailSender(fail_with=EmailNotSentError("sin conexión"))
    service = _service(db_session, sender)
    delivery_id = await _claim(service, user)
    await service.deliver([delivery_id], user.id, NOW)
    retry_at = (await _delivery(db_session, delivery_id, user)).next_attempt_at
    assert retry_at is not None

    sender.fail_with = None
    await service.claim(user.id, KIND, "reminder:1", retry_at)
    await service.deliver([delivery_id], user.id, retry_at)

    delivery = await _delivery(db_session, delivery_id, user)
    assert delivery.status == DeliveryStatus.SENT
    assert delivery.attempts == 2
    assert len(sender.sent) == 1


@pytest.mark.asyncio
async def test_job_with_another_users_id_does_not_touch_the_delivery(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    # B2: el trabajo carga siempre por id y user_id.
    sender = RecordingEmailSender()
    service = _service(db_session, sender)
    delivery_id = await _claim(service, user)

    await service.deliver([delivery_id], other_user.id, NOW)

    assert sender.sent == []
    assert (await _delivery(db_session, delivery_id, user)).status == (
        DeliveryStatus.CLAIMED
    )


@pytest.mark.asyncio
async def test_deleted_account_gives_up_without_retries(
    db_session: AsyncSession, user: CurrentUser
):
    sender = RecordingEmailSender()
    service = _service(db_session, sender, email=None)
    delivery_id = await _claim(service, user)

    await service.deliver([delivery_id], user.id, NOW)

    delivery = await _delivery(db_session, delivery_id, user)
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.next_attempt_at is None
    assert sender.sent == []


@pytest.mark.asyncio
async def test_reason_that_disappeared_sends_nothing_and_leaves_no_claim(
    db_session: AsyncSession, user: CurrentUser
):
    sender = RecordingEmailSender()
    service = _service(db_session, sender, composer=FakeComposer(reason_gone=True))
    delivery_id = await _claim(service, user)

    await service.deliver([delivery_id], user.id, NOW)

    assert sender.sent == []
    assert (
        await NotificationDeliveryRepository(db_session).get(delivery_id, user.id)
        is None
    )


@pytest.mark.asyncio
async def test_kind_without_composer_gives_up(
    db_session: AsyncSession, user: CurrentUser
):
    sender = RecordingEmailSender()
    service = NotificationDeliveryService(
        db_session, email_sender=sender, identities=FakeIdentities()
    )
    delivery_id = await _claim(service, user)

    await service.deliver([delivery_id], user.id, NOW)

    delivery = await _delivery(db_session, delivery_id, user)
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.next_attempt_at is None
    assert sender.sent == []


@pytest.mark.asyncio
async def test_send_job_carries_only_ids_and_a_single_attempt(
    db_session: AsyncSession, user: CurrentUser
):
    queue = InMemoryJobQueue()
    service = NotificationDeliveryService(db_session)
    delivery_id = await _claim(service, user)

    await service.enqueue_send(queue, [delivery_id], user.id)

    [job] = queue.jobs
    assert job.job == SEND_NOTIFICATION
    assert job.max_attempts == 1
    assert job.kwargs == {"delivery_ids": str(delivery_id), "user_id": str(user.id)}


class UnavailableQueue(InMemoryJobQueue):
    async def enqueue(
        self,
        job: str,
        *,
        timeout_seconds: int,
        max_attempts: int,
        key: str | None = None,
        **kwargs: JobArg,
    ) -> bool:
        raise QueueUnavailableError("valkey caído")


@pytest.mark.asyncio
async def test_queue_down_after_the_claim_does_not_fail(
    db_session: AsyncSession, user: CurrentUser
):
    # La entrega queda reclamada y el barrido de abandonados la da por perdida.
    service = NotificationDeliveryService(db_session)
    delivery_id = await _claim(service, user)

    await service.enqueue_send(UnavailableQueue(), [delivery_id], user.id)

    assert (await _delivery(db_session, delivery_id, user)).status == (
        DeliveryStatus.CLAIMED
    )


def test_no_sweeps_are_scheduled_without_smtp():
    # B11 (RNF-34): sin SMTP no se reclama nada que nunca vaya a salir.
    assert notification_cron_jobs(email_enabled=False) == []
    assert notification_cron_jobs(email_enabled=True)
