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

from app.api.auth_rate_limit import rules_for
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
    # El navegador solo puede leerla si la respuesta la expone (CORS).
    assert blocked.headers["Access-Control-Expose-Headers"] == "Retry-After"


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
    # una ventana de 3 s para no esperar una hora. Con 1 s era intermitente: si los
    # tres intentos tardaban más de un segundo, el primero ya había caducado.
    monkeypatch.setitem(
        rate_limits.AUTH_RULES,
        "/auth/signin",
        (RateRule("signin", "2 per 3 seconds", RateKey.EMAIL),),
    )
    email = f"frenada-{uuid.uuid4()}@example.com"
    await real_auth_client.post(
        "/auth/signup", json=form(email=email, password=PASSWORD), headers=EP
    )
    real_auth_client.cookies.clear()
    await _signin(real_auth_client, email)
    await _signin(real_auth_client, email)
    assert (await _signin(real_auth_client, email, PASSWORD)).status_code == 429

    await asyncio.sleep(3.1)

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
    assert blocked.headers["Access-Control-Expose-Headers"] == "Retry-After"


# --- Resto de reglas de /auth/* y rutas equivalentes (cierre de F11) ----------


@pytest.mark.asyncio
async def test_sixth_signup_from_the_same_ip_in_an_hour_is_429(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
):
    # Registro: 5 por hora y por IP (límites y abuso §2, valores iniciales).
    for i in range(5):
        response = await real_auth_client.post(
            "/auth/signup",
            json=form(email=f"alta{i}-{uuid.uuid4()}@example.com", password=PASSWORD),
            headers=EP,
        )
        assert response.json()["status"] == "OK"
        real_auth_client.cookies.clear()

    blocked = await real_auth_client.post(
        "/auth/signup",
        json=form(email=f"alta-extra-{uuid.uuid4()}@example.com", password=PASSWORD),
        headers=EP,
    )

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"


async def _request_reset(client: AsyncClient, email: str, path: str = ""):
    return await client.post(
        path or "/auth/user/password/reset/token",
        json=form(email=email),
        headers=EP,
    )


@pytest.mark.asyncio
async def test_fourth_password_reset_for_the_same_email_is_429(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
):
    # Recuperación: 3 por hora y por email. Da igual que la cuenta exista.
    email = f"nadie-{uuid.uuid4()}@example.com"
    statuses = [
        (await _request_reset(real_auth_client, email)).status_code for _ in range(3)
    ]

    blocked = await _request_reset(real_auth_client, email.upper())

    assert statuses == [200, 200, 200]
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_eleventh_password_reset_from_the_same_ip_is_429(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter
):
    # Recuperación: 10 por hora y por IP, con emails distintos.
    for i in range(10):
        response = await _request_reset(
            real_auth_client, f"r{i}-{uuid.uuid4()}@example.com"
        )
        assert response.status_code == 200

    blocked = await _request_reset(real_auth_client, f"r-{uuid.uuid4()}@example.com")

    assert blocked.status_code == 429


# SuperTokens atiende la misma API con el tenant en la ruta (/auth/<tenant>/…) y
# con una barra final (normaliza la ruta). El límite tiene que valer también ahí,
# o basta con cambiar la URL para saltárselo.
SIGNIN_VARIANTS = ["/auth/public/signin", "/auth/signin/"]
RESET_VARIANTS = [
    "/auth/public/user/password/reset/token",
    "/auth/user/password/reset/token/",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", SIGNIN_VARIANTS)
async def test_signin_ip_limit_also_covers_equivalent_paths(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter, path: str
):
    for i in range(10):
        await _signin(real_auth_client, f"v{i}-{uuid.uuid4()}@example.com")

    blocked = await real_auth_client.post(
        path,
        json=form(email=f"v-{uuid.uuid4()}@example.com", password="mala-clave-1"),
        headers=EP,
    )

    assert blocked.status_code == 429


@pytest.mark.asyncio
@pytest.mark.parametrize("path", RESET_VARIANTS)
async def test_password_reset_email_limit_also_covers_equivalent_paths(
    real_auth_client: AsyncClient, limiter: LimitsRateLimiter, path: str
):
    email = f"nadie-{uuid.uuid4()}@example.com"
    for _ in range(3):
        await _request_reset(real_auth_client, email)

    blocked = await _request_reset(real_auth_client, email, path)

    assert blocked.status_code == 429


@pytest.mark.parametrize(
    ("path", "rules"),
    [
        ("/auth/signin", rate_limits.AUTH_RULES["/auth/signin"]),
        ("/auth/signin/", rate_limits.AUTH_RULES["/auth/signin"]),
        ("/auth/public/signin", rate_limits.AUTH_RULES["/auth/signin"]),
        ("/Auth//otro-tenant/SignIn/", rate_limits.AUTH_RULES["/auth/signin"]),
        (
            "/auth/public/user/email/verify/token",
            rate_limits.AUTH_RULES["/auth/user/email/verify/token"],
        ),
        ("/auth/session/refresh", None),
        ("/auth/a/b/signin", None),
        ("/api/v1/signin", None),
    ],
)
def test_rules_for_recognises_equivalent_paths(
    path: str, rules: tuple[RateRule, ...] | None
):
    assert rules_for(path) == rules


@pytest.mark.asyncio
async def test_unsubscribe_is_limited_per_ip(
    anonymous_client: AsyncClient,
    limiter: LimitsRateLimiter,
    monkeypatch: pytest.MonkeyPatch,
):
    # Público y sin sesión: sin límite por IP, cualquiera cargaría la BD (§4).
    monkeypatch.setattr(
        deps, "UNSUBSCRIBE_PER_IP", RateRule("unsubscribe", "2/minute", RateKey.IP)
    )
    url = "/api/v1/notifications/unsubscribe"

    statuses = [
        (await anonymous_client.get(url, params={"token": "x.y.z"})).status_code
        for _ in range(2)
    ]
    blocked = await anonymous_client.post(url, params={"token": "x.y.z"})

    assert statuses == [400, 400]
    assert blocked.status_code == 429
    assert blocked.headers["Access-Control-Expose-Headers"] == "Retry-After"
