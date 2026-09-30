import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlalchemy import Select, String, and_, cast, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.notifications import (
    REMINDER_KEY_PREFIX,
    DeliveryChannel,
    DeliveryStatus,
    NotificationKind,
)
from app.domain.reminder import ReminderStatus
from app.models.application import Application
from app.models.notification_delivery import NotificationDelivery
from app.models.reminder import Reminder
from app.models.user import User

ReminderSort = Literal["due_at", "created_at"]


@dataclass(frozen=True)
class DueReminder:
    """Un candidato del barrido de recordatorios vencidos. Lleva el id de
    SuperTokens para preguntar si el email está verificado sin otra consulta."""

    reminder_id: uuid.UUID
    user_id: uuid.UUID
    due_at: datetime
    supertokens_user_id: str


@dataclass(frozen=True)
class ReminderFilters:
    """Filtros del listado (RF-52). Objeto plano: el repository no depende de HTTP."""

    application_id: uuid.UUID | None = None
    statuses: list[str] = field(default_factory=list)
    due_before: datetime | None = None
    due_after: datetime | None = None


class ReminderRepository:
    """Acceso a `reminders`. Todo método recibe `user_id` y filtra por él (invariante 1).

    Nunca hace commit: la transacción la confirma el service. La solicitud enlazada
    se carga siempre de forma explícita (joinedload): la relación es lazy="raise".
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, reminder: Reminder) -> Reminder:
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def get(self, user_id: uuid.UUID, reminder_id: uuid.UUID) -> Reminder | None:
        return await self.session.scalar(
            select(Reminder)
            .options(joinedload(Reminder.application))
            .where(Reminder.user_id == user_id, Reminder.id == reminder_id)
            .execution_options(populate_existing=True)
        )

    async def count(self, user_id: uuid.UUID) -> int:
        """Para el límite (especificación §10): todos los estados, también los
        hechos y descartados (decisión 0011)."""
        total = await self.session.scalar(
            select(func.count())
            .select_from(Reminder)
            .where(Reminder.user_id == user_id)
        )
        return total or 0

    async def delete(self, reminder: Reminder) -> None:
        await self.session.delete(reminder)
        await self.session.flush()

    async def list(
        self,
        user_id: uuid.UUID,
        filters: ReminderFilters,
        *,
        page: int,
        limit: int,
        sort_by: ReminderSort,
        descending: bool,
    ) -> tuple[list[Reminder], int]:
        query = self._filtered(user_id, filters)

        total = await self.session.scalar(
            select(func.count()).select_from(
                query.with_only_columns(Reminder.id).subquery()
            )
        )

        sort_column = {"due_at": Reminder.due_at, "created_at": Reminder.created_at}[
            sort_by
        ]
        order = sort_column.desc() if descending else sort_column.asc()

        result = await self.session.scalars(
            query.options(joinedload(Reminder.application))
            .order_by(order, Reminder.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return list(result.all()), total or 0

    def _filtered(
        self, user_id: uuid.UUID, filters: ReminderFilters
    ) -> Select[tuple[Reminder]]:
        query = select(Reminder).where(Reminder.user_id == user_id)

        if filters.application_id:
            query = query.where(Reminder.application_id == filters.application_id)
        if filters.statuses:
            query = query.where(Reminder.status.in_(filters.statuses))
        if filters.due_before:
            query = query.where(Reminder.due_at <= filters.due_before)
        if filters.due_after:
            query = query.where(Reminder.due_at >= filters.due_after)

        return query

    async def save(self, reminder: Reminder) -> Reminder:
        """Envía a la BD los cambios de un recordatorio ya cargado (UPDATE)."""
        await self.session.flush()
        return reminder

    async def get_for_notification(
        self, user_id: uuid.UUID, reminder_id: uuid.UUID
    ) -> Reminder | None:
        """El recordatorio con su solicitud y la empresa de esta: el email de aviso
        dice de qué candidatura es (RF-80)."""
        return await self.session.scalar(
            select(Reminder)
            .options(joinedload(Reminder.application).joinedload(Application.company))
            .where(Reminder.user_id == user_id, Reminder.id == reminder_id)
        )

    async def list_due_for_notification(
        self,
        *,
        notify_after: datetime,
        now: datetime,
        after: tuple[datetime, uuid.UUID] | None,
        limit: int,
    ) -> Sequence[DueReminder]:
        """Candidatos del barrido de RF-80: recordatorios pendientes cuyo momento de
        aviso (la fecha menos la antelación de la cuenta) cayó en
        `(notify_after, now]`, de cuentas con el aviso activado, y sin una entrega que
        impida avisar (reclamada, enviada, desconocida, o fallida sin reintento que
        ya toque). Paginado por `(due_at, id)` con `after`.

        Recorre los recordatorios de todos los usuarios a propósito: es un barrido
        del sistema, y cada fila lleva su `user_id` para todo lo que venga después.
        """
        delivery = NotificationDelivery
        blocking_delivery = (
            select(delivery.id)
            .where(
                delivery.user_id == Reminder.user_id,
                delivery.kind == NotificationKind.REMINDER_DUE,
                delivery.channel == DeliveryChannel.EMAIL,
                delivery.dedupe_key
                == literal(REMINDER_KEY_PREFIX) + cast(Reminder.id, String),
                or_(
                    delivery.status != DeliveryStatus.FAILED,
                    delivery.next_attempt_at.is_(None),
                    delivery.next_attempt_at > now,
                ),
            )
            .exists()
        )
        # El momento del aviso: la fecha menos la antelación de la cuenta (RF-80).
        notify_at = Reminder.due_at - func.make_interval(
            0, 0, 0, 0, User.reminder_notice_hours
        )
        query = (
            select(
                Reminder.id, Reminder.user_id, Reminder.due_at, User.supertokens_user_id
            )
            .join(User, User.id == Reminder.user_id)
            .where(
                Reminder.status == ReminderStatus.PENDING,
                notify_at > notify_after,
                notify_at <= now,
                User.notify_reminder_due.is_(True),
                ~blocking_delivery,
            )
        )
        if after is not None:
            after_due_at, after_id = after
            query = query.where(
                or_(
                    Reminder.due_at > after_due_at,
                    and_(Reminder.due_at == after_due_at, Reminder.id > after_id),
                )
            )
        rows = await self.session.execute(
            query.order_by(Reminder.due_at, Reminder.id).limit(limit)
        )
        return [DueReminder(*row) for row in rows.all()]
