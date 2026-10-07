"""Propuestas de IA (F15, ia.md): llamar al proveedor y el barrido que cierra o
reencola las que se quedaron atascadas (segundo plano §3)."""

from datetime import UTC, datetime
from uuid import UUID

from saq import CronJob

from app.jobs.context import WorkerContext
from app.services.ai_proposal_service import AiProposalService

AI_SWEEP_TIMEOUT_SECONDS = 60


async def run_ai_proposal(
    ctx: WorkerContext, *, proposal_id: str, user_id: str
) -> None:
    """Solo ids (segundo plano §2): la tarea, el modelo y el idioma salen de la
    fila; el perfil y la oferta se leen al ejecutar."""
    async with ctx["session_factory"]() as session:
        await AiProposalService(session, providers=ctx["llm_providers"]).run(
            UUID(user_id), UUID(proposal_id), datetime.now(UTC)
        )


async def sweep_ai_proposals(ctx: WorkerContext) -> None:
    async with ctx["session_factory"]() as session:
        await AiProposalService(session).sweep(ctx["job_queue"], datetime.now(UTC))


def ai_cron_jobs() -> list[CronJob[WorkerContext]]:
    """Siempre: aunque la instalación deje de tener IA, las que quedaron en cola
    o en curso tienen que cerrarse."""
    return [
        CronJob(
            sweep_ai_proposals,
            cron="*/5 * * * *",
            timeout=AI_SWEEP_TIMEOUT_SECONDS,
            retries=1,
        )
    ]
