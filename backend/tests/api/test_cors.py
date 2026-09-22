import pytest
from httpx import AsyncClient

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
