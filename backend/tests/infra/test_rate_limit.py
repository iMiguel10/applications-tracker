import logging

import pytest

from app.infra.rate_limit import LimitsRateLimiter, storage_uri_from_valkey_url


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


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("redis://valkey:6379/0", "async+valkey://valkey:6379/0"),
        ("rediss://user:pw@host:6380/1", "async+valkeys://user:pw@host:6380/1"),
    ],
)
def test_storage_uri_from_valkey_url(url: str, expected: str):
    assert storage_uri_from_valkey_url(url) == expected
