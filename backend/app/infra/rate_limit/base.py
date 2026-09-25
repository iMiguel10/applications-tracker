from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    # Segundos hasta que vuelva a permitirse (Retry-After). 0 si se permite.
    retry_after: int = 0


ALLOWED = RateLimitResult(allowed=True)


class RateLimiter(Protocol):
    """Cuenta una petición contra una regla (`"10/minute"`) y dice si se permite.

    `identifiers` agrupa las peticiones: la regla y la IP, el email o el usuario.
    Nunca lanza por un fallo del almacén: si Valkey no responde, se permite y se
    registra (decisión del usuario en F11: mejor sin rate limit un rato que nadie
    pueda iniciar sesión).
    """

    async def hit(self, limit: str, *identifiers: str) -> RateLimitResult: ...
