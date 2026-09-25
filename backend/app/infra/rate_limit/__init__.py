from app.core.config import Settings
from app.infra.rate_limit.base import ALLOWED, RateLimiter, RateLimitResult
from app.infra.rate_limit.disabled import DisabledRateLimiter
from app.infra.rate_limit.limits_backend import (
    LimitsRateLimiter,
    storage_uri_from_valkey_url,
)

__all__ = [
    "ALLOWED",
    "DisabledRateLimiter",
    "LimitsRateLimiter",
    "RateLimitResult",
    "RateLimiter",
    "build_rate_limiter",
]


def build_rate_limiter(settings: Settings) -> RateLimiter:
    """Solo lo llama quien cablea (el lifespan de main.py)."""
    if not settings.rate_limit_enabled:
        return DisabledRateLimiter()
    return LimitsRateLimiter(storage_uri_from_valkey_url(settings.valkey_url))
