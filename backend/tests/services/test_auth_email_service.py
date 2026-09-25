"""Email de recuperación de contraseña, sin core ni SMTP: identidades falsas y
`RecordingEmailSender`. La parte que habla con el core real está en
tests/api/test_password_reset.py."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.email import EmailDeliveryUnknownError, EmailError, EmailNotSentError
from app.infra.email.disabled import DisabledEmailSender
from app.infra.email.recording import RecordingEmailSender
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.auth_email_service import AuthEmailService

EMAIL = "persona@example.com"
LINK = "http://localhost:5173/reset-password?token=t0k3n&tenantId=public"


VERIFY_LINK = "http://localhost:5173/verify-email?token=v3r1fy&tenantId=public"


class FakeIdentities(IdentityRepository):
    def __init__(self, *, email: str | None = EMAIL, verified: bool = False) -> None:
        self.email = email
        self.verified = verified
        self.links_created = 0

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return self.email

    async def create_password_reset_link(
        self, supertokens_user_id: str, email: str, tenant_id: str
    ) -> str | None:
        self.links_created += 1
        return LINK

    async def create_email_verification_link(
        self, supertokens_user_id: str, email: str, tenant_id: str
    ) -> str | None:
        # Como el core: ya verificado, no hay enlace.
        return None if self.verified else VERIFY_LINK


async def _send(
    db_session: AsyncSession,
    user: CurrentUser,
    *,
    sender: RecordingEmailSender | DisabledEmailSender | None = None,
    identities: FakeIdentities | None = None,
    language_hint: str | None = None,
) -> RecordingEmailSender | DisabledEmailSender:
    sender = sender or RecordingEmailSender()
    service = AuthEmailService(
        db_session, email_sender=sender, identities=identities or FakeIdentities()
    )
    await service.send_password_reset(
        supertokens_user_id=user.supertokens_user_id,
        tenant_id="public",
        language_hint=language_hint,
    )
    return sender


async def _set_language(
    db_session: AsyncSession, user: CurrentUser, language: str | None
) -> None:
    row = await UserRepository(db_session).get_by_id(user.id)
    assert row is not None
    row.language = language
    await db_session.flush()


@pytest.mark.asyncio
async def test_sends_the_link_to_the_account_email(
    db_session: AsyncSession, user: CurrentUser
):
    sender = await _send(db_session, user)

    assert isinstance(sender, RecordingEmailSender)
    [email] = sender.sent
    assert email.to == EMAIL
    assert LINK in email.text
    assert email.html is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("account_language", "hint", "expected_subject"),
    [
        # T15: el idioma de la cuenta manda sobre el del navegador.
        ("en", "es", "Reset your Applications Tracker password"),
        ("es", "en", "Restablece tu contraseña de Applications Tracker"),
        # Sin idioma fijado, el del navegador que lo pidió.
        (None, "en", "Reset your Applications Tracker password"),
        # Sin ninguno de los dos (o con uno no soportado), español.
        (None, None, "Restablece tu contraseña de Applications Tracker"),
        (None, "fr", "Restablece tu contraseña de Applications Tracker"),
    ],
)
async def test_language_is_account_then_browser_then_default(
    db_session: AsyncSession,
    user: CurrentUser,
    account_language: str | None,
    hint: str | None,
    expected_subject: str,
):
    await _set_language(db_session, user, account_language)

    sender = await _send(db_session, user, language_hint=hint)

    assert isinstance(sender, RecordingEmailSender)
    assert sender.sent[0].subject == expected_subject


@pytest.mark.asyncio
async def test_without_smtp_no_token_is_created(
    db_session: AsyncSession, user: CurrentUser
):
    identities = FakeIdentities()

    await _send(db_session, user, sender=DisabledEmailSender(), identities=identities)

    assert identities.links_created == 0


@pytest.mark.asyncio
async def test_deleted_identity_sends_nothing(
    db_session: AsyncSession, user: CurrentUser
):
    identities = FakeIdentities(email=None)

    sender = await _send(db_session, user, identities=identities)

    assert isinstance(sender, RecordingEmailSender)
    assert sender.sent == []
    assert identities.links_created == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error", [EmailNotSentError("rechazado"), EmailDeliveryUnknownError("corte")]
)
async def test_send_failures_are_logged_not_raised(
    db_session: AsyncSession,
    user: CurrentUser,
    error: EmailError,
    caplog: pytest.LogCaptureFixture,
):
    # Un solo intento: si fallara el trabajo, SAQ no lo reintentaría igualmente, y
    # el usuario puede volver a pedirlo. Lo que importa es que quede registrado,
    # con el id y sin la dirección.
    await _send(db_session, user, sender=RecordingEmailSender(fail_with=error))

    assert user.supertokens_user_id in caplog.text
    assert EMAIL not in caplog.text


async def _send_verification(
    db_session: AsyncSession,
    user: CurrentUser,
    *,
    identities: FakeIdentities,
    language_hint: str | None = None,
) -> RecordingEmailSender:
    sender = RecordingEmailSender()
    await AuthEmailService(
        db_session, email_sender=sender, identities=identities
    ).send_verification(
        supertokens_user_id=user.supertokens_user_id,
        tenant_id="public",
        language_hint=language_hint,
    )
    return sender


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("account_language", "expected_subject"),
    [
        ("en", "Confirm your email for Applications Tracker"),
        ("es", "Confirma tu email en Applications Tracker"),
    ],
)
async def test_verification_email_in_the_account_language(
    db_session: AsyncSession,
    user: CurrentUser,
    account_language: str,
    expected_subject: str,
):
    # T15 para la verificación: mismo canal, mismas reglas de idioma.
    await _set_language(db_session, user, account_language)

    sender = await _send_verification(
        db_session, user, identities=FakeIdentities(), language_hint="fr"
    )

    [email] = sender.sent
    assert email.subject == expected_subject
    assert VERIFY_LINK in email.text
    assert "24" in email.text


@pytest.mark.asyncio
async def test_already_verified_sends_nothing(
    db_session: AsyncSession, user: CurrentUser
):
    # Un reenvío que llega al worker después de verificar no molesta con otro email.
    sender = await _send_verification(
        db_session, user, identities=FakeIdentities(verified=True)
    )

    assert sender.sent == []
