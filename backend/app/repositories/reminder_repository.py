import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.reminder import Reminder

ReminderSort = Literal["due_at", "created_at"]


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
