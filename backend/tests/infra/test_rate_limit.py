import logging

import pytest

from app.infra.rate_limit import LimitsRateLimiter, storage_uri_from_valkey_url
from app.infra.rate_limit.limits_backend import STORE_RETRY_SECONDS


@pytest.mark.asyncio
async def test_blocks_after_the_limit_and_says_how_long_to_wait():
    limiter = LimitsRateLimiter("async+memory://")

    results = [
        await limiter.hit("2/minute", "signin", "ip", "1.2.3.4") for _ in range(3)
    ]

    assert [r.allowed for r in results] == [True, True, False]
    assert 0 < results[2].retry_after <= 60
    # Otra clave tiene su propia cuenta.
    assert (await limiter.hit("2/minute", "signin", "ip", "5.6.7.8")).allowed


@pytest.mark.asyncio
async def test_lets_requests_through_when_the_store_fails(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
):
    # Decisión del usuario en F11: con Valkey caído, mejor sin rate limit un rato
    # que nadie pueda iniciar sesión. Queda en el log.
    limiter = LimitsRateLimiter("async+memory://")

    async def down(*args: object) -> bool:
        raise ConnectionError("valkey caído")

    monkeypatch.setattr(limiter._limiter, "hit", down)

    with caplog.at_level(logging.WARNING):
        result = await limiter.hit("1/minute", "signin", "ip", "1.2.3.4")

    assert result.allowed
    assert "sin almacén" in caplog.text


@pytest.mark.asyncio
async def test_stops_asking_a_failed_store_for_a_while(
    monkeypatch: pytest.MonkeyPatch,
):
    # Con Valkey caído, cada consulta espera el timeout de conexión (~4 s). Tras
    # un fallo se deja de preguntar un rato; pasado ese rato, se vuelve a probar.
    now = [1000.0]
    limiter = LimitsRateLimiter("async+memory://", clock=lambda: now[0])
    calls = 0

    async def down(*args: object) -> bool:
        nonlocal calls
        calls += 1
        raise ConnectionError("valkey caído")

    monkeypatch.setattr(limiter._limiter, "hit", down)

    for _ in range(5):
        assert (await limiter.hit("1/minute", "signin", "ip", "1.2.3.4")).allowed
    assert calls == 1

    now[0] += STORE_RETRY_SECONDS
    monkeypatch.undo()
    first = await limiter.hit("1/minute", "signin", "ip", "1.2.3.4")
    second = await limiter.hit("1/minute", "signin", "ip", "1.2.3.4")

    assert first.allowed
    assert not second.allowed


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("redis://valkey:6379/0", "async+valkey://valkey:6379/0"),
        ("rediss://user:pw@host:6380/1", "async+valkeys://user:pw@host:6380/1"),
    ],
)
def test_storage_uri_from_valkey_url(url: str, expected: str):
    assert storage_uri_from_valkey_url(url) == expected
