"""Cambiar el email de una cuenta desde la administración (`scripts/change_email.py`,
derecho de rectificación), contra el core real de SuperTokens."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.email import EmailSender
from app.infra.email.disabled import DisabledEmailSender
from app.infra.email.recording import RecordingEmailSender
from app.repositories.identity_repository import IdentityRepository
from app.services.account_provisioning_service import (
    AccountExistsError,
    AccountNotFoundError,
    AccountProvisioningService,
    InvalidEmailError,
)
from tests.auth_helpers import PASSWORD, form

EP = {"rid": "emailpassword"}


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}@example.com"


async def _signup(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/auth/signup", json=form(email=email, password=PASSWORD), headers=EP
    )
    assert response.json()["status"] == "OK"
    client.cookies.clear()


async def _signin_status(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/auth/signin",
        json=form(email=email, password=PASSWORD),
        headers=EP | {"st-auth-mode": "header"},
    )
    return str(response.json()["status"])


def _service(
    session: AsyncSession, sender: EmailSender | None = None
) -> AccountProvisioningService:
    return AccountProvisioningService(
        session, sender or DisabledEmailSender(), IdentityRepository()
    )


@pytest.mark.asyncio
async def test_signs_in_with_the_new_email_already_verified(
    real_auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    old, new = _email("old"), _email("new")
    await _signup(real_auth_client, old)

    notified = await _service(db_session).change_email(old, new)

    assert notified is False  # sin SMTP no hay aviso
    assert await _signin_status(real_auth_client, new) == "OK"
    assert await _signin_status(real_auth_client, old) == "WRONG_CREDENTIALS_ERROR"
    identities = IdentityRepository()
    supertokens_id = await identities.find_id_by_email(new)
    assert supertokens_id is not None
    assert await identities.is_email_verified(supertokens_id) is True
    assert await identities.get_email(supertokens_id) == new


@pytest.mark.asyncio
async def test_an_email_in_use_changes_nothing(
    real_auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    first, second = _email("first"), _email("second")
    await _signup(real_auth_client, first)
    await _signup(real_auth_client, second)

    with pytest.raises(AccountExistsError):
        await _service(db_session).change_email(first, second)

    assert await _signin_status(real_auth_client, first) == "OK"


@pytest.mark.asyncio
async def test_an_unknown_account(
    real_auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    with pytest.raises(AccountNotFoundError):
        await _service(db_session).change_email(_email("nobody"), _email("new"))


@pytest.mark.parametrize("bad", ["", "no-es-un-email", "a@", "@b.es", "a b@c.es"])
@pytest.mark.asyncio
async def test_an_invalid_new_email_changes_nothing(
    real_auth_client: AsyncClient, db_session: AsyncSession, bad: str
) -> None:
    email = _email("keep")
    await _signup(real_auth_client, email)

    with pytest.raises(InvalidEmailError):
        await _service(db_session).change_email(email, bad)

    assert await _signin_status(real_auth_client, email) == "OK"


@pytest.mark.asyncio
async def test_with_email_the_old_address_is_told(
    real_auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    # Si el nuevo no es de la titular (una errata, una suplantación), quien lo
    # controle podría quedarse con la cuenta: la dirección antigua se entera.
    old, new = _email("old"), _email("new")
    await _signup(real_auth_client, old)
    sender = RecordingEmailSender()

    notified = await _service(db_session, sender).change_email(old, new)

    assert notified is True
    [notice] = sender.sent
    assert notice.to == old
    assert "n***@example.com" in notice.text
    assert new not in notice.text


@pytest.mark.asyncio
async def test_a_failed_change_tells_nobody(
    real_auth_client: AsyncClient, db_session: AsyncSession
) -> None:
    first, second = _email("first"), _email("second")
    await _signup(real_auth_client, first)
    await _signup(real_auth_client, second)
    sender = RecordingEmailSender()

    with pytest.raises(AccountExistsError):
        await _service(db_session, sender).change_email(first, second)

    assert sender.sent == []
