"""`AccountProvisioningService` sin el core: qué hace cuando no hay correo o el
envío falla (imprimir el enlace) y con el idioma (decisión 0022). Contra el core
real, en `tests/api/test_signup_closed.py`."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import Language
from app.infra.email import EmailNotSentError
from app.infra.email.disabled import DisabledEmailSender
from app.infra.email.recording import RecordingEmailSender
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.services.account_provisioning_service import (
    AccountExistsError,
    AccountProvisioningService,
)

LINK = "http://localhost:5173/reset-password?token=abc&tenantId=public"


class FakeIdentities(IdentityRepository):
    def __init__(self) -> None:
        self.accounts: dict[str, str] = {}
        self.verified: set[str] = set()
        self.passwords: list[str] = []

    async def create_account(self, email: str, password: str) -> str | None:
        if email in self.accounts:
            return None
        self.passwords.append(password)
        self.accounts[email] = f"st-{len(self.accounts) + 1}"
        return self.accounts[email]

    async def mark_email_verified(self, supertokens_user_id: str, email: str) -> None:
        self.verified.add(supertokens_user_id)

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return next(
            (
                email
                for email, sid in self.accounts.items()
                if sid == supertokens_user_id
            ),
            None,
        )

    async def create_password_reset_link(
        self, supertokens_user_id: str, email: str, tenant_id: str
    ) -> str | None:
        return LINK


@pytest.mark.asyncio
async def test_without_email_the_link_is_returned_to_hand_over(
    db_session: AsyncSession,
):
    identities = FakeIdentities()

    created = await AccountProvisioningService(
        db_session, DisabledEmailSender(), identities
    ).create("ana@example.com", None)

    assert (created.email_sent, created.link) == (False, LINK)
    sid = identities.accounts["ana@example.com"]
    assert sid in identities.verified
    user = await UserRepository(db_session).get_by_supertokens_id(sid)
    assert user is not None and user.id == created.user_id
    # Una contraseña aleatoria y larga que nadie ve.
    assert len(identities.passwords[0]) >= 32


@pytest.mark.asyncio
async def test_a_failed_email_falls_back_to_the_link(db_session: AsyncSession):
    sender = RecordingEmailSender(fail_with=EmailNotSentError("no salió"))

    created = await AccountProvisioningService(
        db_session, sender, FakeIdentities()
    ).create("ana@example.com", None)

    assert (created.email_sent, created.link) == (False, LINK)


@pytest.mark.asyncio
async def test_the_welcome_email_uses_the_chosen_language(db_session: AsyncSession):
    sender = RecordingEmailSender()

    created = await AccountProvisioningService(
        db_session, sender, FakeIdentities()
    ).create("ana@example.com", Language.EN)

    assert (created.email_sent, created.link) == (True, None)
    [email] = sender.sent
    assert email.subject == "Your Applications Tracker account is ready"
    assert LINK in email.text
    # No es el email de recuperación: no dice que alguien lo haya pedido.
    assert "asked to reset" not in email.text


@pytest.mark.asyncio
async def test_an_existing_email_is_not_created_twice(db_session: AsyncSession):
    identities = FakeIdentities()
    service = AccountProvisioningService(db_session, DisabledEmailSender(), identities)
    await service.create("ana@example.com", None)

    with pytest.raises(AccountExistsError):
        await service.create("ana@example.com", None)
    assert len(identities.accounts) == 1
