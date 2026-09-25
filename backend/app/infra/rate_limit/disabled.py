from app.infra.rate_limit.base import ALLOWED, RateLimitResult


class DisabledRateLimiter:
    """Deja pasar todo. Para las pruebas que no prueban el rate limit
    (`RATE_LIMIT_ENABLED=false`) y como valor por defecto antes del lifespan."""

    async def hit(self, limit: str, *identifiers: str) -> RateLimitResult:
        return ALLOWED
