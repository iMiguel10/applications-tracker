"""Recuperación de contraseña contra el core real (autenticación §8: T9, T10, T11,
T14). La API encola; aquí se ejecuta a mano el service del trabajo, con
`RecordingEmailSender`, para leer el enlace del email."""

import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import InMemoryJobQueue, JobArg, QueueUnavailableError
from app.jobs.auth_emails import SEND_PASSWORD_RESET_EMAIL
from app.main import app
from app.services.auth_email_service import AuthEmailService
from tests.auth_helpers import BASE_URL, HEADERS, PASSWORD, form

NEW_PASSWORD = "nueva-clave-42"
EP = {"rid": "emailpassword"}


def _queue() -> InMemoryJobQueue:
    queue = app.state.job_queue
    assert isinstance(queue, InMemoryJobQueue)
    return queue


async def _signup(client: AsyncClient) -> str:
    email = f"reset-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/signup", json=form(email=email, password=PASSWORD), headers=EP
    )
    assert response.json()["status"] == "OK"
    return email


async def _request_reset(
    client: AsyncClient, email: str, **headers: str
) -> httpx.Response:
    return await client.post(
        "/auth/user/password/reset/token",
        json=form(email=email),
        headers=EP | headers,
    )


async def _run_job(db_session: AsyncSession, kwargs: dict[str, JobArg]) -> str:
    """Hace lo que haría el worker y devuelve el enlace del email enviado."""
    sender = RecordingEmailSender()
    await AuthEmailService(db_session, email_sender=sender).send_password_reset(
        supertokens_user_id=str(kwargs["supertokens_user_id"]),
        tenant_id=str(kwargs["tenant_id"]),
        language_hint=None,
    )
    [email] = sender.sent
    return next(line for line in email.text.splitlines() if "reset-password" in line)


async def _reset(client: AsyncClient, link: str, password: str) -> httpx.Response:
    token = parse_qs(urlparse(link).query)["token"][0]
    return await client.post(
        "/auth/user/password/reset",
        json={"method": "token", "token": token} | form(password=password),
        headers=EP,
    )


@pytest.mark.asyncio
async def test_same_response_whether_the_account_exists_or_not(
    real_auth_client: AsyncClient,
):
    # T9: sin oráculo de cuentas. Solo cambia que se encola un trabajo.
    email = await _signup(real_auth_client)
    real_auth_client.cookies.clear()

    existing = await _request_reset(real_auth_client, email)
    missing = await _request_reset(
        real_auth_client, f"nadie-{uuid.uuid4()}@example.com"
    )

    assert existing.status_code == missing.status_code == 200
    assert existing.json() == missing.json() == {"status": "OK"}
    [job] = _queue().jobs
    assert job.job == SEND_PASSWORD_RESET_EMAIL
    assert job.max_attempts == 1


@pytest.mark.asyncio
async def test_job_carries_ids_and_browser_language_but_no_token(
    real_auth_client: AsyncClient,
):
    email = await _signup(real_auth_client)

    await _request_reset(real_auth_client, email, **{"Accept-Language": "en-GB,en"})

    [job] = _queue().jobs
    # Nada más que esto: el token daría acceso a la cuenta y Valkey guarda los
    # trabajos en disco. El worker genera el enlace al enviar.
    assert set(job.kwargs) == {"supertokens_user_id", "tenant_id", "language_hint"}
    assert job.kwargs["language_hint"] == "en"


@pytest.mark.asyncio
async def test_queue_down_still_answers_the_same(real_auth_client: AsyncClient):
    class DownQueue(InMemoryJobQueue):
        async def enqueue(self, job: str, **kwargs: JobArg) -> bool:  # type: ignore[override]
            raise QueueUnavailableError("valkey caído")

    email = await _signup(real_auth_client)
    app.state.job_queue = DownQueue()

    response = await _request_reset(real_auth_client, email)

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


@pytest.mark.asyncio
async def test_link_points_to_website_domain_and_works_once(
    real_auth_client: AsyncClient, db_session: AsyncSession
):
    email = await _signup(real_auth_client)
    await _request_reset(real_auth_client, email)

    link = await _run_job(db_session, _queue().jobs[0].kwargs)

    # T14: el dominio sale de WEBSITE_DOMAIN, y la ruta es la del frontend.
    assert link.startswith(f"{settings.website_domain}/reset-password?token=")
    assert "tenantId=public" in link
    # T10: un solo uso.
    first = await _reset(real_auth_client, link, NEW_PASSWORD)
    second = await _reset(real_auth_client, link, "otra-clave-43")
    assert first.json() == {"status": "OK"}
    assert second.json()["status"] == "RESET_PASSWORD_INVALID_TOKEN_ERROR"


@pytest.mark.asyncio
async def test_new_password_must_pass_the_signup_policy(
    real_auth_client: AsyncClient, db_session: AsyncSession
):
    email = await _signup(real_auth_client)
    await _request_reset(real_auth_client, email)
    link = await _run_job(db_session, _queue().jobs[0].kwargs)

    response = await _reset(real_auth_client, link, "corta")

    assert response.json()["status"] == "FIELD_ERROR"


@pytest.mark.asyncio
async def test_reset_revokes_every_existing_session(
    real_auth_client: AsyncClient, db_session: AsyncSession
):
    # T11: una sesión abierta antes (quizá robada) no se puede renovar después.
    email = await _signup(real_auth_client)
    stolen = httpx.Cookies(real_auth_client.cookies)
    real_auth_client.cookies.clear()
    await _request_reset(real_auth_client, email)
    link = await _run_job(db_session, _queue().jobs[0].kwargs)

    assert (await _reset(real_auth_client, link, NEW_PASSWORD)).json()["status"] == "OK"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL,
        headers=HEADERS,
        cookies=stolen,
    ) as thief:
        refresh = await thief.post("/auth/session/refresh", headers={"rid": "session"})
    assert refresh.status_code == 401

    # Y la contraseña nueva es la que vale.
    signin = await real_auth_client.post(
        "/auth/signin", json=form(email=email, password=NEW_PASSWORD), headers=EP
    )
    assert signin.json()["status"] == "OK"
