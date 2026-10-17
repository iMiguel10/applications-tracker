"""Registro cerrado (`SIGNUP_ENABLED=false`, decisión 0022), contra el core real:
nadie se crea una cuenta por la API, en ninguna de sus URL, y las que ya existen
siguen funcionando. Las crea quien administra con `scripts/create_user.py`."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import InMemoryJobQueue
from app.main import app
from app.repositories.identity_repository import IdentityRepository
from app.services.account_provisioning_service import (
    AccountExistsError,
    AccountProvisioningService,
)
from tests.auth_helpers import PASSWORD, form


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path", ["/auth/signup", "/auth/signup/", "/auth/public/signup"]
)
async def test_with_signup_closed_no_url_creates_an_account(
    real_auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, path: str
):
    # El cierre está en la operación (el override), no en una ruta: SuperTokens
    # atiende la misma en varias URL (como el rate limit de F11).
    monkeypatch.setattr(settings, "signup_enabled", False)
    email = _email("closed")

    response = await real_auth_client.post(
        path,
        json=form(email=email, password=PASSWORD),
        headers={"rid": "emailpassword"},
    )

    assert response.json() == {"status": "GENERAL_ERROR", "message": "signup_disabled"}
    assert await IdentityRepository().find_id_by_email(email) is None
    # Ni email de verificación encolado.
    queue = app.state.job_queue
    assert isinstance(queue, InMemoryJobQueue)
    assert queue.jobs == []


@pytest.mark.asyncio
async def test_existing_accounts_still_sign_in_with_signup_closed(
    real_auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    email = _email("existing")
    created = await real_auth_client.post(
        "/auth/signup",
        json=form(email=email, password=PASSWORD),
        headers={"rid": "emailpassword"},
    )
    assert created.json()["status"] == "OK"
    real_auth_client.cookies.clear()
    monkeypatch.setattr(settings, "signup_enabled", False)

    signin = await real_auth_client.post(
        "/auth/signin", json=form(email=email, password=PASSWORD)
    )
    me = await real_auth_client.get("/api/v1/me")

    assert signin.json()["status"] == "OK"
    assert me.status_code == 200
    assert me.json()["email"] == email


@pytest.mark.asyncio
async def test_the_admin_creates_a_verified_account_even_with_signup_closed(
    real_auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # real_auth_client: solo para tener el core real inicializado y la sesión de
    # la BD de pruebas.
    monkeypatch.setattr(settings, "signup_enabled", False)
    email = _email("admin-created")
    sender = RecordingEmailSender()
    identities = IdentityRepository()

    created = await AccountProvisioningService(db_session, sender, identities).create(
        email, None
    )

    supertokens_id = await identities.find_id_by_email(email)
    assert supertokens_id is not None
    assert await identities.is_email_verified(supertokens_id) is True
    assert created.email_sent is True
    [welcome] = sender.sent
    assert welcome.to == email
    assert "/reset-password?token=" in welcome.text
    with pytest.raises(AccountExistsError):
        await AccountProvisioningService(db_session, sender, identities).create(
            email, None
        )
