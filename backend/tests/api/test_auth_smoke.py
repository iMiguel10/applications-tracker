import uuid

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.auth_helpers import BASE_URL, HEADERS, PASSWORD, form


@pytest.mark.asyncio
async def test_signup_me_and_signout_revokes_refresh_token(
    real_auth_client: AsyncClient,
):
    # T7 (humo con el core real).
    email = f"smoke-{uuid.uuid4()}@example.com"

    signup = await real_auth_client.post(
        "/auth/signup",
        json=form(email=email, password=PASSWORD),
        headers={"rid": "emailpassword"},
    )
    assert signup.json()["status"] == "OK"

    me = await real_auth_client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["email"] == email

    # Copia de las cookies antes del logout, como si alguien las hubiera robado.
    stolen = httpx.Cookies(real_auth_client.cookies)

    signout = await real_auth_client.post("/auth/signout", headers={"rid": "session"})
    assert signout.json()["status"] == "OK"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL,
        headers=HEADERS,
        cookies=stolen,
    ) as thief:
        refresh = await thief.post("/auth/session/refresh", headers={"rid": "session"})

    # El refresh token quedó revocado: la sesión no se puede renovar. El access
    # token copiado sigue valiendo hasta caducar (5 min, decisión 0002).
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_header_mode_login_gives_bearer_token_that_authenticates(
    real_auth_client: AsyncClient,
):
    # Contrato para integraciones y Swagger (decisión 0003): tokens en cabeceras
    # y Authorization: Bearer, sin cookies de por medio.
    email = f"smoke-{uuid.uuid4()}@example.com"
    await real_auth_client.post(
        "/auth/signup",
        json=form(email=email, password=PASSWORD),
        headers={"rid": "emailpassword"},
    )
    real_auth_client.cookies.clear()

    signin = await real_auth_client.post(
        "/auth/signin",
        json=form(email=email, password=PASSWORD),
        headers={"st-auth-mode": "header"},
    )
    access_token = signin.headers.get("st-access-token")

    assert signin.json()["status"] == "OK"
    assert access_token
    assert "sAccessToken" not in signin.cookies

    me = await real_auth_client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == email


@pytest.mark.asyncio
async def test_signin_with_wrong_password_is_rejected(real_auth_client: AsyncClient):
    email = f"smoke-{uuid.uuid4()}@example.com"
    await real_auth_client.post(
        "/auth/signup",
        json=form(email=email, password=PASSWORD),
        headers={"rid": "emailpassword"},
    )

    response = await real_auth_client.post(
        "/auth/signin",
        json=form(email=email, password="otra-clave-9"),
        headers={"rid": "emailpassword"},
    )

    assert response.json()["status"] == "WRONG_CREDENTIALS_ERROR"
