"""Cambiar la contraseña con la actual (issue #2) contra el core real de SuperTokens:
la actual se comprueba, la nueva pasa la política del backend, las demás sesiones
se cierran y, con correo, se encola el aviso solo con ids."""

import uuid
from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.deps import get_password_service
from app.infra.queue import InMemoryJobQueue
from app.infra.rate_limit import DisabledRateLimiter, LimitsRateLimiter
from app.main import app
from app.services.password_service import (
    SEND_PASSWORD_CHANGED_EMAIL,
    PasswordService,
)
from tests.auth_helpers import BASE_URL, HEADERS, PASSWORD, form

NEW_PASSWORD = "otra-clave-77"
EP = {"rid": "emailpassword"}
URL = "/api/v1/me/password"


async def _signup(client: AsyncClient) -> str:
    """Crea la cuenta y deja su sesión (cookies) en el cliente."""
    email = f"pw-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/signup", json=form(email=email, password=PASSWORD), headers=EP
    )
    assert response.json()["status"] == "OK"
    return email


async def _signin_status(client: AsyncClient, email: str, password: str) -> str:
    """Inicia sesión en modo cabecera, sin tocar las cookies del cliente."""
    response = await client.post(
        "/auth/signin",
        json=form(email=email, password=password),
        headers=EP | {"st-auth-mode": "header"},
    )
    return str(response.json()["status"])


def _change(current: str, new: str) -> dict[str, str]:
    return {"current_password": current, "new_password": new}


@pytest.fixture
def limiter() -> Iterator[LimitsRateLimiter]:
    limiter = LimitsRateLimiter("async+memory://")
    app.state.rate_limiter = limiter
    yield limiter
    app.state.rate_limiter = DisabledRateLimiter()


@pytest.fixture
def email_enabled() -> Iterator[InMemoryJobQueue]:
    """Como si la instalación tuviera correo: el service encola el aviso."""
    queue = app.state.job_queue
    assert isinstance(queue, InMemoryJobQueue)
    app.dependency_overrides[get_password_service] = lambda: PasswordService(
        queue, email_enabled=True
    )
    yield queue
    app.dependency_overrides.pop(get_password_service, None)


@pytest.mark.asyncio
async def test_changes_the_password(real_auth_client: AsyncClient) -> None:
    email = await _signup(real_auth_client)

    response = await real_auth_client.post(URL, json=_change(PASSWORD, NEW_PASSWORD))

    assert response.status_code == 204
    assert await _signin_status(real_auth_client, email, NEW_PASSWORD) == "OK"
    assert (
        await _signin_status(real_auth_client, email, PASSWORD)
        == "WRONG_CREDENTIALS_ERROR"
    )


@pytest.mark.asyncio
async def test_a_wrong_current_password_changes_nothing(
    real_auth_client: AsyncClient,
) -> None:
    email = await _signup(real_auth_client)

    response = await real_auth_client.post(
        URL, json=_change("no-es-la-actual-1", NEW_PASSWORD)
    )

    assert response.status_code == 400
    assert response.json()["code"] == "wrong_current_password"
    assert await _signin_status(real_auth_client, email, PASSWORD) == "OK"


@pytest.mark.parametrize("new", ["corta1", "sinnumeros", "", "a1" * 200])
@pytest.mark.asyncio
async def test_the_new_password_must_meet_the_policy(
    real_auth_client: AsyncClient, new: str
) -> None:
    # La política vive solo en el backend (invariante 7): 8 a 100 caracteres, con
    # letras y números. Vacía o enorme, el mismo error, sin llegar al 422 de
    # Pydantic (que devolvería la contraseña en el cuerpo).
    email = await _signup(real_auth_client)

    response = await real_auth_client.post(URL, json=_change(PASSWORD, new))

    assert response.status_code == 422
    assert response.json()["code"] == "password_policy"
    assert await _signin_status(real_auth_client, email, PASSWORD) == "OK"


@pytest.mark.asyncio
async def test_an_invalid_body_never_echoes_the_passwords(
    real_auth_client: AsyncClient,
) -> None:
    await _signup(real_auth_client)
    secret = "mi-secreto-" + "x" * 300

    responses = [
        await real_auth_client.post(URL, json=_change(secret, "")),
        await real_auth_client.post(URL, json={"current_password": secret}),
    ]

    for response in responses:
        assert secret not in response.text
        assert "mi-secreto" not in response.text


@pytest.mark.asyncio
async def test_closes_the_other_sessions_and_keeps_this_one(
    real_auth_client: AsyncClient,
) -> None:
    email = await _signup(real_auth_client)
    # Otra sesión de la misma cuenta en otro dispositivo: su propio cliente, porque
    # un inicio de sesión en modo cabecera borra las cookies del que lo hace.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL, headers=HEADERS
    ) as other_device:
        other = await other_device.post(
            "/auth/signin",
            json=form(email=email, password=PASSWORD),
            headers=EP | {"st-auth-mode": "header"},
        )
        refresh_token = other.headers["st-refresh-token"]

        response = await real_auth_client.post(
            URL, json=_change(PASSWORD, NEW_PASSWORD)
        )

        assert response.status_code == 204
        refreshed = await other_device.post(
            "/auth/session/refresh",
            headers={
                "Authorization": f"Bearer {refresh_token}",
                "st-auth-mode": "header",
            },
        )
        assert refreshed.status_code == 401
    # La de esta petición sigue sirviendo.
    assert (await real_auth_client.get("/api/v1/me")).status_code == 200


@pytest.mark.asyncio
async def test_without_email_nothing_is_enqueued(
    real_auth_client: AsyncClient,
) -> None:
    await _signup(real_auth_client)
    queue = app.state.job_queue
    assert isinstance(queue, InMemoryJobQueue)

    await real_auth_client.post(URL, json=_change(PASSWORD, NEW_PASSWORD))

    assert not [job for job in queue.jobs if job.job == SEND_PASSWORD_CHANGED_EMAIL]


@pytest.mark.asyncio
async def test_with_email_the_notice_carries_only_ids(
    real_auth_client: AsyncClient, email_enabled: InMemoryJobQueue
) -> None:
    await _signup(real_auth_client)

    await real_auth_client.post(URL, json=_change(PASSWORD, NEW_PASSWORD))

    [job] = [j for j in email_enabled.jobs if j.job == SEND_PASSWORD_CHANGED_EMAIL]
    # Valkey guarda los trabajos en disco: ni contraseñas ni tokens (CLAUDE.md).
    assert set(job.kwargs) == {"supertokens_user_id", "changed_at"}
    assert PASSWORD not in str(job.kwargs)
    assert NEW_PASSWORD not in str(job.kwargs)


@pytest.mark.asyncio
async def test_a_wrong_current_password_sends_no_notice(
    real_auth_client: AsyncClient, email_enabled: InMemoryJobQueue
) -> None:
    await _signup(real_auth_client)

    await real_auth_client.post(URL, json=_change("no-es-la-actual-1", NEW_PASSWORD))

    assert not [
        job for job in email_enabled.jobs if job.job == SEND_PASSWORD_CHANGED_EMAIL
    ]


@pytest.mark.asyncio
async def test_sixth_attempt_in_fifteen_minutes_is_429(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
) -> None:
    # Cuenta todos los intentos: si no, se podría adivinar la actual desde una
    # sesión abierta.
    await _signup(real_auth_client)

    codes = [
        (
            await real_auth_client.post(
                URL, json=_change(f"intento-{i}-x", NEW_PASSWORD)
            )
        ).status_code
        for i in range(6)
    ]

    assert codes == [400] * 5 + [429]


@pytest.mark.asyncio
async def test_requires_a_session(anonymous_client: AsyncClient) -> None:
    response = await anonymous_client.post(URL, json=_change(PASSWORD, NEW_PASSWORD))

    assert response.status_code == 401
