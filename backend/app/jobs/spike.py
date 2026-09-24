"""DESECHABLE (F9): el trabajo del esqueleto vertical. Ver services/spike_service.py."""

import uuid

from app.jobs.context import WorkerContext
from app.repositories.identity_repository import IdentityRepository
from app.services.spike_service import SpikePdfService


async def generate_spike_pdf(ctx: WorkerContext, *, user_id: str, file_id: str) -> None:
    async with ctx["session_factory"]() as session:
        service = SpikePdfService(
            session,
            pdf_renderer=ctx["pdf_renderer"],
            storage=ctx["storage"],
            email_sender=ctx["email_sender"],
            identities=IdentityRepository(),
            api_url=ctx["api_url"],
        )
        await service.generate_and_send(uuid.UUID(user_id), uuid.UUID(file_id))
