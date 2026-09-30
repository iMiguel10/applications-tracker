"""Ficheros (F13, ficheros §5): el barrido diario de huérfanos."""

from datetime import UTC, datetime

from saq import CronJob

from app.jobs.context import WorkerContext
from app.services.orphan_file_service import OrphanFileService

# Recorre todo el almacén: más margen que los barridos de avisos. Si no terminara,
# lo que quedase lo recoge la pasada del día siguiente.
ORPHAN_SWEEP_TIMEOUT_SECONDS = 600


async def sweep_orphan_files(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await OrphanFileService(session, ctx["storage"]).sweep(datetime.now(UTC))


def file_cron_jobs() -> list[CronJob[WorkerContext]]:
    """Siempre, con correo o sin él (a diferencia de los avisos): los ficheros
    huérfanos ocupan disco en cualquier instalación."""
    return [
        CronJob(
            sweep_orphan_files,
            # Cada día a las 4:15 UTC, lejos de la limpieza de entregas (3:30).
            cron="15 4 * * *",
            timeout=ORPHAN_SWEEP_TIMEOUT_SECONDS,
            retries=1,
        )
    ]
