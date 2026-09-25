import logging
import math
import time
from functools import cache

from limits import RateLimitItem, parse
from limits.aio.strategies import MovingWindowRateLimiter
from limits.storage import storage_from_string

from app.infra.rate_limit.base import ALLOWED, RateLimitResult

logger = logging.getLogger(__name__)


@cache
def _parse(limit: str) -> RateLimitItem:
    return parse(limit)


def storage_uri_from_valkey_url(url: str) -> str:
    """`redis://valkey:6379/0` (VALKEY_URL, la de SAQ) → `async+valkey://…`, el
    almacén asíncrono de `limits` con el cliente oficial de Valkey."""
    scheme, _, rest = url.partition("://")
    secure = scheme in {"rediss", "valkeys"}
    return f"async+{'valkeys' if secure else 'valkey'}://{rest}"


class LimitsRateLimiter:
    """`RateLimiter` con la librería `limits` y ventana deslizante (A28): con
    ventanas fijas, alguien podría concentrar el doble de peticiones justo en el
    cambio de ventana (las de la última al final y las de la nueva al principio).

    En las pruebas se usa con `async+memory://`, sin Valkey.
    """

    def __init__(self, storage_uri: str) -> None:
        self._limiter = MovingWindowRateLimiter(storage_from_string(storage_uri))

    async def hit(self, limit: str, *identifiers: str) -> RateLimitResult:
        item = _parse(limit)
        try:
            if await self._limiter.hit(item, *identifiers):
                return ALLOWED
            stats = await self._limiter.get_window_stats(item, *identifiers)
        except Exception:
            # Sin almacén no hay rate limit, pero la aplicación sigue funcionando.
            logger.warning("Rate limit sin almacén; se deja pasar", exc_info=True)
            return ALLOWED
        retry_after = max(1, math.ceil(stats.reset_time - time.time()))
        return RateLimitResult(allowed=False, retry_after=retry_after)
