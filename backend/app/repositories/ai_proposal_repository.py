import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ai import IN_FLIGHT_STATUSES, AiTask, KeySource, ProposalStatus
from app.models.ai_proposal import AiProposal


class AiProposalRepository:
    """Acceso a `ai_proposals`. Todo método sobre datos de un usuario recibe
    `user_id` y filtra por él (invariante 1); los del barrido recorren todas las
    cuentas. Nunca hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, proposal: AiProposal) -> AiProposal:
        self.session.add(proposal)
        await self.session.flush()
        return proposal

    async def get(
        self, user_id: uuid.UUID, application_id: uuid.UUID, proposal_id: uuid.UUID
    ) -> AiProposal | None:
        return await self.session.scalar(
            select(AiProposal).where(
                AiProposal.id == proposal_id,
                AiProposal.user_id == user_id,
                AiProposal.application_id == application_id,
            )
        )

    async def get_by_id(
        self, user_id: uuid.UUID, proposal_id: uuid.UUID
    ) -> AiProposal | None:
        return await self.session.scalar(
            select(AiProposal).where(
                AiProposal.id == proposal_id, AiProposal.user_id == user_id
            )
        )

    async def list_for_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID, limit: int
    ) -> Sequence[AiProposal]:
        """Las más recientes primero."""
        result = await self.session.scalars(
            select(AiProposal)
            .where(
                AiProposal.user_id == user_id,
                AiProposal.application_id == application_id,
            )
            .order_by(AiProposal.created_at.desc(), AiProposal.id.desc())
            .limit(limit)
        )
        return result.all()

    async def count_platform_usage(self, user_id: uuid.UUID, kind: AiTask) -> int:
        """Usos gratuitos gastados de una tarea: lo facturado con la clave de la
        plataforma **más lo que está en curso**. Sin lo segundo, cinco peticiones
        lanzadas a la vez con un solo uso restante verían todas "queda 1" y las
        cinco acabarían facturadas (ia.md §6, trampa)."""
        in_flight = [status.value for status in IN_FLIGHT_STATUSES]
        count = await self.session.scalar(
            select(func.count())
            .select_from(AiProposal)
            .where(
                AiProposal.user_id == user_id,
                AiProposal.kind == kind.value,
                AiProposal.key_source == KeySource.PLATFORM.value,
                or_(AiProposal.billable, AiProposal.status.in_(in_flight)),
            )
        )
        return count or 0

    async def claim(
        self, user_id: uuid.UUID, proposal_id: uuid.UUID, now: datetime
    ) -> AiProposal | None:
        """La pasa de `queued` a `running` en una sola sentencia y la devuelve. Si la
        misma propuesta se ejecuta dos veces a la vez (SAQ puede relanzar un
        trabajo), solo una la encuentra en cola: la otra recibe None y no llama al
        proveedor, que facturaría dos veces."""
        result = await self.session.scalars(
            update(AiProposal)
            .where(
                AiProposal.id == proposal_id,
                AiProposal.user_id == user_id,
                AiProposal.status == ProposalStatus.QUEUED.value,
            )
            .values(status=ProposalStatus.RUNNING.value, started_at=now)
            .returning(AiProposal)
            .execution_options(populate_existing=True)
        )
        return result.one_or_none()

    async def finish(
        self, user_id: uuid.UUID, proposal_id: uuid.UUID, values: dict[str, Any]
    ) -> bool:
        """Cierra una propuesta en curso con su resultado. Es un UPDATE condicionado
        y no un objeto cargado: si mientras se llamaba al proveedor se borró la
        solicitud o la cuenta, o el barrido la dio por colgada, no actualiza nada
        (False) en lugar de fallar o de pisar el cierre del barrido."""
        result = await self.session.execute(
            update(AiProposal)
            .where(
                AiProposal.id == proposal_id,
                AiProposal.user_id == user_id,
                AiProposal.status == ProposalStatus.RUNNING.value,
            )
            .values(**values)
        )
        return bool(getattr(result, "rowcount", 0))

    async def stale(
        self,
        status: ProposalStatus,
        before: datetime,
        limit: int,
        *,
        after: tuple[datetime, uuid.UUID] | None = None,
    ) -> Sequence[AiProposal]:
        """En `status` desde antes de `before`, de todas las cuentas (el barrido).
        Las en cola se miden por `updated_at`; las en curso, por `started_at`. Las
        bloqueadas se saltan. `after` es el último par de la página anterior."""
        column = (
            AiProposal.started_at
            if status == ProposalStatus.RUNNING
            else AiProposal.updated_at
        )
        query = select(AiProposal).where(
            AiProposal.status == status.value, column < before
        )
        if after is not None:
            query = query.where(tuple_(column, AiProposal.id) > after)
        result = await self.session.scalars(
            query.order_by(column, AiProposal.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.all()
