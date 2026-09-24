from dataclasses import dataclass

from app.infra.queue.base import JobArg


@dataclass(frozen=True)
class EnqueuedJob:
    job: str
    kwargs: dict[str, JobArg]
    timeout_seconds: int
    max_attempts: int
    key: str | None


class InMemoryJobQueue:
    """`JobQueue` de pruebas: registra lo encolado y no ejecuta nada. Las pruebas
    llaman a las funciones de `jobs/` directamente (arquitectura de la v2 §6)."""

    def __init__(self) -> None:
        self.jobs: list[EnqueuedJob] = []

    async def enqueue(
        self,
        job: str,
        *,
        timeout_seconds: int,
        max_attempts: int,
        key: str | None = None,
        **kwargs: JobArg,
    ) -> bool:
        if key is not None and any(queued.key == key for queued in self.jobs):
            return False
        self.jobs.append(
            EnqueuedJob(job, dict(kwargs), timeout_seconds, max_attempts, key)
        )
        return True
