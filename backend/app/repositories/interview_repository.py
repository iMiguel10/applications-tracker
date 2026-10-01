import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Row,
    Select,
    String,
    and_,
    cast,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interview import InterviewOutcome
from app.domain.notifications import (
    INTERVIEW_KEY_PREFIX,
    DeliveryChannel,
    DeliveryStatus,
    NotificationKind,
)
from app.models.application import Application
from app.models.company import Company
from app.models.interview import Interview
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User


@dataclass(frozen=True)
class UpcomingInterview:
    """Un candidato del barrido de entrevistas próximas."""

    interview_id: uuid.UUID
    user_id: uuid.UUID
    scheduled_at: datetime
    supertokens_user_id: str


class InterviewRepository:
    """Acceso a `interviews`. Es una tabla hija (vía `application_id`): se filtra
    haciendo join con `applications` para exigir también `user_id` (arquitectura §7).

    Nunca hace commit: la transacción la confirma el service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, interview: Interview) -> Interview:
        self.session.add(interview)
        await self.session.flush()
        return interview

    async def get(
        self, user_id: uuid.UUID, application_id: uuid.UUID, interview_id: uuid.UUID
    ) -> Interview | None:
        return await self.session.scalar(
            select(Interview)
            .join(Application, Application.id == Interview.application_id)
            .where(
                Application.user_id == user_id,
                Interview.application_id == application_id,
                Interview.id == interview_id,
            )
        )

    async def list_for_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> list[Interview]:
        result = await self.session.scalars(
            select(Interview)
            .join(Application, Application.id == Interview.application_id)
            .where(
                Application.user_id == user_id,
                Interview.application_id == application_id,
            )
            .order_by(Interview.scheduled_at)
        )
        return list(result.all())

    async def list_upcoming(
        self, user_id: uuid.UUID, *, after: datetime, limit: int
    ) -> Sequence[Row[tuple[Interview, Application, Company]]]:
        """RF-63: próximas entrevistas del usuario (cualquier solicitud), con la
        solicitud y la empresa para mostrarlas sin una consulta por fila.

        Sin relación declarada `Interview.application` (no hace falta fuera de
        aquí): se hace explícito con un `select` de las tres tablas.
        """
        result = await self.session.execute(
            self._upcoming(user_id, after=after)
            .order_by(Interview.scheduled_at.asc())
            .limit(limit)
        )
        return result.all()

    async def count_upcoming(self, user_id: uuid.UUID, *, after: datetime) -> int:
        """Total de próximas entrevistas, sin el límite de `list_upcoming` (para el
        "N más" del widget del dashboard)."""
        total = await self.session.scalar(
            select(func.count()).select_from(
                self._upcoming(user_id, after=after)
                .with_only_columns(Interview.id)
                .subquery()
            )
        )
        return total or 0

    async def list_between(
        self, user_id: uuid.UUID, *, start: datetime, end: datetime
    ) -> Sequence[Row[tuple[Interview, Application, Company]]]:
        """Entrevistas que empiezan en [start, end), con su solicitud y su empresa
        (calendario, RF-130). Las canceladas no: ya no van a ocurrir."""
        result = await self.session.execute(
            select(Interview, Application, Company)
            .join(Application, Application.id == Interview.application_id)
            .join(Company, Company.id == Application.company_id)
            .where(
                Application.user_id == user_id,
                Interview.scheduled_at >= start,
                Interview.scheduled_at < end,
                Interview.outcome != InterviewOutcome.CANCELLED.value,
            )
            .order_by(Interview.scheduled_at, Interview.id)
        )
        return result.all()

    def _upcoming(
        self, user_id: uuid.UUID, *, after: datetime
    ) -> Select[tuple[Interview, Application, Company]]:
        return (
            select(Interview, Application, Company)
            .join(Application, Application.id == Interview.application_id)
            .join(Company, Company.id == Application.company_id)
            .where(
                Application.user_id == user_id,
                Interview.scheduled_at >= after,
                Interview.outcome == InterviewOutcome.PENDING.value,
            )
        )

    async def save(self, interview: Interview) -> Interview:
        await self.session.flush()
        return interview

    async def delete(self, interview: Interview) -> None:
        await self.session.delete(interview)
        await self.session.flush()

    async def get_for_notification(
        self, user_id: uuid.UUID, interview_id: uuid.UUID
    ) -> Row[tuple[Interview, Application, Company]] | None:
        """La entrevista con su solicitud y empresa, para el email de aviso (RF-81)."""
        result = await self.session.execute(
            select(Interview, Application, Company)
            .join(Application, Application.id == Interview.application_id)
            .join(Company, Company.id == Application.company_id)
            .where(Application.user_id == user_id, Interview.id == interview_id)
        )
        return result.first()

    async def list_upcoming_for_notification(
        self,
        *,
        now: datetime,
        after: tuple[datetime, uuid.UUID] | None,
        limit: int,
    ) -> Sequence[UpcomingInterview]:
        """Candidatos del barrido de RF-81: entrevistas pendientes que aún no han
        empezado y cuyo momento de aviso (la hora menos la antelación de la cuenta)
        ya llegó, de cuentas con el aviso activado y sin una entrega que lo impida
        para **esa hora**. Paginado por `(scheduled_at, id)` con `after`.

        Sin límite hacia atrás, a diferencia de los recordatorios: una entrevista
        futura siempre merece su aviso, aunque se programe dentro de la antelación,
        y como solo cuentan las que aún no han empezado, el día que se activa el
        canal no hay nada acumulado que enviar.

        Recorre las entrevistas de todos los usuarios a propósito: es un barrido del
        sistema, y cada fila lleva su `user_id` para todo lo que venga después.
        """
        delivery = NotificationDelivery
        seconds = cast(
            func.floor(func.extract("epoch", Interview.scheduled_at)), BigInteger
        )
        blocking_delivery = (
            select(delivery.id)
            .where(
                delivery.user_id == Application.user_id,
                delivery.kind == NotificationKind.INTERVIEW_UPCOMING,
                delivery.channel == DeliveryChannel.EMAIL,
                delivery.dedupe_key
                == literal(INTERVIEW_KEY_PREFIX)
                + cast(Interview.id, String)
                + literal(":")
                + cast(seconds, String),
                or_(
                    delivery.status != DeliveryStatus.FAILED,
                    delivery.next_attempt_at.is_(None),
                    delivery.next_attempt_at > now,
                ),
            )
            .exists()
        )
        notify_at = Interview.scheduled_at - func.make_interval(
            0, 0, 0, 0, User.interview_notice_hours
        )
        query = (
            select(
                Interview.id,
                Application.user_id,
                Interview.scheduled_at,
                User.supertokens_user_id,
            )
            .join(Application, Application.id == Interview.application_id)
            .join(User, User.id == Application.user_id)
            .where(
                Interview.outcome == InterviewOutcome.PENDING.value,
                Interview.scheduled_at > now,
                notify_at <= now,
                User.notify_interview.is_(True),
                ~blocking_delivery,
            )
        )
        if after is not None:
            after_at, after_id = after
            query = query.where(
                or_(
                    Interview.scheduled_at > after_at,
                    and_(Interview.scheduled_at == after_at, Interview.id > after_id),
                )
            )
        rows = await self.session.execute(
            query.order_by(Interview.scheduled_at, Interview.id).limit(limit)
        )
        return [UpcomingInterview(*row) for row in rows.all()]
