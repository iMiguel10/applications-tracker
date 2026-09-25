"""Rate limiting por la API (RNF-04, límites y abuso §2: L4, L5, L6).

El resto de pruebas corren sin rate limit (`DisabledRateLimiter`, el valor por
defecto de `app.state`): con límites reales fallarían de forma intermitente por 429.
Aquí cada prueba pone un limitador en memoria nuevo.
"""

import asyncio
import uuid
from collections.abc import Iterator

import pytest
from httpx import AsyncClient

from app.api.v1 import deps
from app.core.config import settings
from app.domain import rate_limits
from app.domain.rate_limits import RateKey, RateRule
from app.infra.rate_limit import DisabledRateLimiter, LimitsRateLimiter
from app.main import app
from tests.auth_helpers import PASSWORD, form

EP = {"rid": "emailpassword"}


@pytest.fixture
def limiter() -> Iterator[LimitsRateLimiter]:
    limiter = LimitsRateLimiter("async+memory://")
    app.state.rate_limiter = limiter
    yield limiter
    app.state.rate_limiter = DisabledRateLimiter()


async def _signin(
    client: AsyncClient, email: str, password: str = "mala-clave-1", **headers: str
):
    return await client.post(
        "/auth/signin", json=form(email=email, password=password), headers=EP | headers
    )


@pytest.mark.asyncio
async def test_eleventh_signin_from_the_same_ip_is_429(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
):
    # L4: 10 por minuto y por IP; cada intento con un email distinto, para que no
    # salte antes el límite por email.
    for i in range(10):
        response = await _signin(real_auth_client, f"a{i}-{uuid.uuid4()}@example.com")
        assert response.status_code == 200

    blocked = await _signin(real_auth_client, f"b-{uuid.uuid4()}@example.com")

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"
    assert int(blocked.headers["Retry-After"]) == blocked.json()["retry_after"] > 0


@pytest.mark.asyncio
async def test_a_correct_signin_still_works_behind_the_middleware(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
):
    # L4: el middleware lee el cuerpo (para el email) y lo vuelve a inyectar. Si se
    # lo comiera, SuperTokens recibiría un cuerpo vacío.
    email = f"ok-{uuid.uuid4()}@example.com"
    await real_auth_client.post(
        "/auth/signup", json=form(email=email, password=PASSWORD), headers=EP
    )
    real_auth_client.cookies.clear()

    response = await _signin(real_auth_client, email, PASSWORD)

    assert response.json()["status"] == "OK"


@pytest.mark.asyncio
async def test_spoofed_forwarded_for_does_not_dodge_the_ip_limit(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
):
    # L5: sin proxy de confianza, X-Forwarded-For se ignora.
    for i in range(10):
        await _signin(
            real_auth_client,
            f"c{i}-{uuid.uuid4()}@example.com",
            **{"X-Forwarded-For": f"198.51.100.{i}"},
        )

    blocked = await _signin(
        real_auth_client,
        f"d-{uuid.uuid4()}@example.com",
        **{"X-Forwarded-For": "198.51.100.99"},
    )

    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_per_email_limit_applies_across_ips_behind_a_trusted_proxy(
    real_auth_client: AsyncClient,
    limiter: LimitsRateLimiter,
    monkeypatch: pytest.MonkeyPatch,
):
    # Detrás del proxy propio, cada intento llega de una IP distinta: lo que frena a
    # quien prueba contraseñas de UNA cuenta desde muchas IPs es el límite por email.
    monkeypatch.setattr(settings, "trusted_proxies", "127.0.0.1")
    email = f"victima-{uuid.uuid4()}@example.com"
    for i in range(10):
        response = await _signin(
            real_auth_client, email, **{"X-Forwarded-For": f"198.51.100.{i}"}
        )
        assert response.status_code == 200

    blocked = await _signin(
        real_auth_client, email.upper(), **{"X-Forwarded-For": "198.51.100.200"}
    )

    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_email_limit_slows_down_but_never_locks_the_account(
    real_auth_client: AsyncClient,
    limiter: LimitsRateLimiter,
    monkeypatch: pytest.MonkeyPatch,
):
    # L6: frenar, no bloquear. Pasada la ventana, la dueña de la cuenta entra. Con
    # una ventana de un segundo para no esperar una hora.
    monkeypatch.setitem(
        rate_limits.AUTH_RULES,
        "/auth/signin",
        (RateRule("signin", "2/second", RateKey.EMAIL),),
    )
    email = f"frenada-{uuid.uuid4()}@example.com"
    await real_auth_client.post(
        "/auth/signup", json=form(email=email, password=PASSWORD), headers=EP
    )
    real_auth_client.cookies.clear()
    await _signin(real_auth_client, email)
    await _signin(real_auth_client, email)
    assert (await _signin(real_auth_client, email, PASSWORD)).status_code == 429

    await asyncio.sleep(1.1)

    assert (await _signin(real_auth_client, email, PASSWORD)).json()["status"] == "OK"


@pytest.mark.asyncio
async def test_resending_the_verification_email_is_limited_per_user(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
):
    await real_auth_client.post(
        "/auth/signup",
        json=form(email=f"reenvio-{uuid.uuid4()}@example.com", password=PASSWORD),
        headers=EP,
    )
    headers = {"rid": "emailverification"}
    statuses = [
        (
            await real_auth_client.post(
                "/auth/user/email/verify/token", headers=headers
            )
        ).status_code
        for _ in range(4)
    ]

    assert statuses == [200, 200, 200, 429]


@pytest.mark.asyncio
async def test_oversized_auth_body_is_rejected(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
):
    response = await real_auth_client.post(
        "/auth/signin", content=b"x" * (65 * 1024), headers=EP
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_general_api_limit_per_user(
    client: AsyncClient, limiter: LimitsRateLimiter, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(deps, "API_PER_USER", RateRule("api", "2/minute", RateKey.USER))

    statuses = [
        (await client.get("/api/v1/me/preferences")).status_code for _ in range(3)
    ]
    blocked = await client.get("/api/v1/me/preferences")

    assert statuses == [200, 200, 429]
    assert blocked.json()["code"] == "rate_limited"
    assert "Retry-After" in blocked.headers
