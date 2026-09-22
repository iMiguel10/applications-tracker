import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app

# Mismo sitio que WEBSITE_DOMAIN (localhost): con otro host, SuperTokens exigiría
# cookies SameSite=None + HTTPS (autenticacion.md §5).
BASE_URL = "http://localhost:8000"
# Como el navegador: supertokens-web-js envía st-auth-mode: cookie en cada petición.
# Sin esa cabecera, el login devolvería los tokens en cabeceras (decisión 0003).
HEADERS = {"Origin": "http://localhost:5173", "st-auth-mode": "cookie"}
PASSWORD = "secreto123"


def _form(email: str, password: str) -> dict[str, list[dict[str, str]]]:
    return {
        "formFields": [
            {"id": "email", "value": email},
            {"id": "password", "value": password},
        ]
    }


@pytest_asyncio.fixture
async def real_auth_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Cliente contra el core real de SuperTokens (supertokens-test)."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL, headers=HEADERS
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_signup_me_and_signout_revokes_refresh_token(
    real_auth_client: AsyncClient,
):
    # T7 (humo con el core real).
    email = f"smoke-{uuid.uuid4()}@example.com"

    signup = await real_auth_client.post(
        "/auth/signup", json=_form(email, PASSWORD), headers={"rid": "emailpassword"}
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
        "/auth/signup", json=_form(email, PASSWORD), headers={"rid": "emailpassword"}
    )
    real_auth_client.cookies.clear()

    signin = await real_auth_client.post(
        "/auth/signin",
        json=_form(email, PASSWORD),
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
        "/auth/signup", json=_form(email, PASSWORD), headers={"rid": "emailpassword"}
    )

    response = await real_auth_client.post(
        "/auth/signin",
        json=_form(email, "otra-clave-9"),
        headers={"rid": "emailpassword"},
    )

    assert response.json()["status"] == "WRONG_CREDENTIALS_ERROR"
