from typing import Any

from redis.exceptions import RedisError
from saq import Queue

from app.infra.queue.base import JobArg, QueueUnavailableError


class SaqJobQueue:
    """`JobQueue` sobre SAQ (A18). Traduce nuestros nombres a los de SAQ."""

    def __init__(self, queue: Queue) -> None:
        self._queue = queue

    async def enqueue(
        self,
        job: str,
        *,
        timeout_seconds: int,
        max_attempts: int,
        key: str | None = None,
        **kwargs: JobArg,
    ) -> bool:
        options: dict[str, Any] = {
            "timeout": timeout_seconds,
            # En SAQ, `retries` es el número TOTAL de intentos, no de reintentos:
            # un trabajo se repite mientras retries > attempts, y attempts ya vale
            # 1 tras el primero. retries=0 no significa "sin reintentos" sino lo
            # mismo que 1. Por eso la interfaz habla de max_attempts.
            "retries": max_attempts,
        }
        if key is not None:
            options["key"] = key
        # SAQ mezcla en el mismo **kwargs las opciones del trabajo y los
        # argumentos de la función: un argumento que se llamara `timeout` o `key`
        # se tomaría por una opción. Pasarlos en `kwargs` explícito lo evita.
        try:
            enqueued = await self._queue.enqueue(job, kwargs=dict(kwargs), **options)
        except (RedisError, OSError) as exc:
            raise QueueUnavailableError(f"{type(exc).__name__}: {exc}") from exc
        return enqueued is not None
