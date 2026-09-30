import logging
import math
import time
from collections.abc import Callable
from functools import cache

from limits import RateLimitItem, parse
from limits.aio.strategies import MovingWindowRateLimiter
from limits.storage import storage_from_string

from app.infra.rate_limit.base import ALLOWED, RateLimitResult

logger = logging.getLogger(__name__)

# Tras un fallo del almacén, cuánto tiempo se deja de consultarlo. Sin esta pausa,
# con Valkey caído cada petición esperaría el timeout de conexión (unos 4 s por
# regla: más de 8 s un inicio de sesión).
STORE_RETRY_SECONDS = 30.0


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

    Si el almacén falla, deja pasar (decisión del usuario en F11) y no vuelve a
    consultarlo hasta pasados `STORE_RETRY_SECONDS`: una sola petición paga el
    timeout y queda una línea en el log por cada intento, no una por petición.
    """

    def __init__(
        self, storage_uri: str, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._limiter = MovingWindowRateLimiter(storage_from_string(storage_uri))
        self._clock = clock
        self._store_down_until: float | None = None

    async def hit(self, limit: str, *identifiers: str) -> RateLimitResult:
        if self._store_down_until is not None:
            if self._clock() < self._store_down_until:
                return ALLOWED
            self._store_down_until = None
        item = _parse(limit)
        try:
            if await self._limiter.hit(item, *identifiers):
                return ALLOWED
            stats = await self._limiter.get_window_stats(item, *identifiers)
        except Exception:
            # Sin almacén no hay rate limit, pero la aplicación sigue funcionando.
            self._store_down_until = self._clock() + STORE_RETRY_SECONDS
            logger.warning(
                "Rate limit sin almacén; se deja pasar durante %.0f s",
                STORE_RETRY_SECONDS,
                exc_info=True,
            )
            return ALLOWED
        retry_after = max(1, math.ceil(stats.reset_time - time.time()))
        return RateLimitResult(allowed=False, retry_after=retry_after)
