import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import String, and_, cast, func, literal, or_, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ai import IN_FLIGHT_STATUSES, AiTask, KeySource, ProposalStatus
from app.domain.notifications import (
    AI_PROPOSAL_KEY_PREFIX,
    DeliveryChannel,
    DeliveryStatus,
    NotificationKind,
)
from app.models.ai_proposal import AiProposal
from app.models.application import Application
from app.models.company import Company
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User


@dataclass(frozen=True)
class FinishedProposal:
    """Un candidato del barrido del aviso de propuesta terminada (RF-157). Lleva el
    id de SuperTokens para preguntar si el email está verificado sin otra consulta."""

    proposal_id: uuid.UUID
    user_id: uuid.UUID
    finished_at: datetime
    supertokens_user_id: str


@dataclass(frozen=True)
class ProposalNotice:
    """Lo que dice el email de una propuesta terminada: nunca su contenido."""

    proposal: AiProposal
    position_title: str
    company_name: str


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
            .values(**values, finished_at=func.clock_timestamp())
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

    # --- Aviso por email al terminar (RF-157) -----------------------------------

    async def list_finished_for_notification(
        self,
        *,
        finished_after: datetime,
        now: datetime,
        after: tuple[datetime, uuid.UUID] | None,
        limit: int,
    ) -> Sequence[FinishedProposal]:
        """Candidatos del barrido de RF-157: propuestas terminadas (con el resultado
        que sea) en `(finished_after, now]`, de cuentas con el aviso activado, y sin
        una entrega que impida avisar (reclamada, enviada, desconocida, o fallida sin
        reintento que ya toque). Paginado por `(finished_at, id)` con `after`.

        Recorre las de todos los usuarios a propósito: es un barrido del sistema, y
        cada fila lleva su `user_id` para todo lo que venga después."""
        delivery = NotificationDelivery
        blocking_delivery = (
            select(delivery.id)
            .where(
                delivery.user_id == AiProposal.user_id,
                delivery.kind == NotificationKind.AI_PROPOSAL_FINISHED,
                delivery.channel == DeliveryChannel.EMAIL,
                delivery.dedupe_key
                == literal(AI_PROPOSAL_KEY_PREFIX) + cast(AiProposal.id, String),
                or_(
                    delivery.status != DeliveryStatus.FAILED,
                    delivery.next_attempt_at.is_(None),
                    delivery.next_attempt_at > now,
                ),
            )
            .exists()
        )
        query = (
            select(
                AiProposal.id,
                AiProposal.user_id,
                AiProposal.finished_at,
                User.supertokens_user_id,
            )
            .join(User, User.id == AiProposal.user_id)
            .where(
                AiProposal.status.not_in(
                    [status.value for status in IN_FLIGHT_STATUSES]
                ),
                AiProposal.finished_at > finished_after,
                AiProposal.finished_at <= now,
                User.notify_ai_proposal.is_(True),
                ~blocking_delivery,
            )
        )
        if after is not None:
            after_finished_at, after_id = after
            query = query.where(
                or_(
                    AiProposal.finished_at > after_finished_at,
                    and_(
                        AiProposal.finished_at == after_finished_at,
                        AiProposal.id > after_id,
                    ),
                )
            )
        rows = await self.session.execute(
            query.order_by(AiProposal.finished_at, AiProposal.id).limit(limit)
        )
        return [FinishedProposal(*row) for row in rows.all()]

    async def get_for_notification(
        self, user_id: uuid.UUID, proposal_id: uuid.UUID
    ) -> ProposalNotice | None:
        """La propuesta con el puesto y la empresa de su solicitud, para el email.
        None si ya no existe (o su solicitud se borró)."""
        row = (
            await self.session.execute(
                select(AiProposal, Application.position_title, Company.name)
                .join(
                    Application,
                    and_(
                        Application.id == AiProposal.application_id,
                        Application.user_id == AiProposal.user_id,
                    ),
                )
                .join(Company, Company.id == Application.company_id)
                .where(AiProposal.id == proposal_id, AiProposal.user_id == user_id)
            )
        ).first()
        if row is None:
            return None
        proposal, position_title, company_name = row
        return ProposalNotice(proposal, position_title, company_name)
