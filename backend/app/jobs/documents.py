"""Documentos generados (F14, segundo plano §2): maquetar un CV pendiente y
el barrido que reencola los que se quedaron atascados (segundo plano §3)."""

from datetime import UTC, datetime
from uuid import UUID

from saq import CronJob

from app.jobs.context import WorkerContext
from app.services.cv_generation_service import CvGenerationService

PENDING_SWEEP_TIMEOUT_SECONDS = 60


async def generate_document(
    ctx: WorkerContext, *, document_id: str, user_id: str
) -> None:
    """Solo ids (segundo plano §2): la foto fija y el diseño salen de la fila."""
    async with ctx["session_factory"]() as session:
        await CvGenerationService(
            session, storage=ctx["storage"], renderer=ctx["pdf_renderer"]
        ).render_pending(UUID(user_id), UUID(document_id))


async def requeue_pending_documents(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await CvGenerationService(session).sweep_pending(
            ctx["job_queue"], datetime.now(UTC)
        )


def document_cron_jobs() -> list[CronJob[WorkerContext]]:
    """Siempre, con correo o sin él: generar no depende del SMTP."""
    return [
        CronJob(
            requeue_pending_documents,
            cron="*/5 * * * *",
            timeout=PENDING_SWEEP_TIMEOUT_SECONDS,
            retries=1,
        )
    ]
