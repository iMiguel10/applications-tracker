from typing import Protocol

# Tipos que viajan como argumento de un trabajo: solo ids y escalares, nunca
# objetos. El trabajo carga lo demás de la BD (segundo plano §2).
JobArg = str | int | float | bool | None


class QueueUnavailableError(Exception):
    """No se pudo encolar (Valkey caído o inalcanzable). Quien encola tras un
    commit NO debe fallar la petición por esto: la fila ya está `pending` y el
    barrido de pendientes la reencola (arquitectura de la v2 §3)."""


class JobQueue(Protocol):
    """Encola trabajos para el `worker`. Se llama siempre DESPUÉS del commit
    (invariante 11): el trabajo puede empezar antes de que esta llamada vuelva.
    """

    async def enqueue(
        self,
        job: str,
        *,
        timeout_seconds: int,
        max_attempts: int,
        key: str | None = None,
        **kwargs: JobArg,
    ) -> bool:
        """Encola `job` con `kwargs`. `max_attempts` cuenta el primer intento:
        1 = nunca se reintenta. Con `key`, si ya hay un trabajo con esa clave en
        la cola, no se encola otro y devuelve False. Lanza QueueUnavailableError
        si la cola no responde."""
        ...
