import uuid

import pytest
from httpx import AsyncClient

from tests.auth_helpers import PASSWORD, form

ALLOWED_ORIGIN = "http://localhost:5173"


@pytest.mark.asyncio
async def test_auth_response_includes_cors_header_for_allowed_origin(
    anonymous_client: AsyncClient,
):
    # T5: si el middleware de SuperTokens quedase por fuera del de CORS, esta
    # respuesta (no la OPTIONS previa) llegaría sin Access-Control-Allow-Origin.
    response = await anonymous_client.post(
        "/auth/signin",
        headers={"Origin": ALLOWED_ORIGIN, "rid": "emailpassword"},
        json={
            "formFields": [
                {"id": "email", "value": "nobody@example.com"},
                {"id": "password", "value": "wrong-password-1"},
            ]
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_preflight_from_unknown_origin_gets_no_cors_headers(
    anonymous_client: AsyncClient,
):
    # T6: la lista de orígenes no está abierta.
    response = await anonymous_client.options(
        "/auth/signin",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_session_response_still_exposes_front_token_to_the_browser(
    real_auth_client: AsyncClient,
):
    # El SDK del navegador lee `front-token` de la respuesta para saber que hay
    # sesión. Con `expose_headers` en el CORSMiddleware, Starlette pisaba la lista
    # de SuperTokens en todas las respuestas y el login no creaba sesión (F11).
    response = await real_auth_client.post(
        "/auth/signup",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "rid": "emailpassword",
            "st-auth-mode": "cookie",
        },
        json=form(email=f"cors-{uuid.uuid4()}@example.com", password=PASSWORD),
    )

    assert response.json()["status"] == "OK"
    exposed = response.headers.get("access-control-expose-headers", "").lower()
    assert "front-token" in [header.strip() for header in exposed.split(",")]
