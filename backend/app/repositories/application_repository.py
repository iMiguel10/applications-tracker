import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload

from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.models.company import Company
from app.repositories.search import LIKE_ESCAPE, contains_pattern

ApplicationSort = Literal[
    "applied_at", "created_at", "updated_at", "company", "position_title"
]


@dataclass(frozen=True)
class ApplicationFilters:
    """Filtros del listado (RF-22). Objeto plano: el repository no depende de HTTP."""

    statuses: Sequence[str] = field(default_factory=tuple)
    company_id: uuid.UUID | None = None
    work_modes: Sequence[str] = field(default_factory=tuple)
    sources: Sequence[str] = field(default_factory=tuple)
    applied_from: date | None = None
    applied_to: date | None = None
    search: str | None = None
    # None: todas; False: solo activas (por defecto en la API); True: solo archivadas.
    archived: bool | None = False


class ApplicationRepository:
    """Acceso a `applications`. Todo método recibe user_id y filtra por él (invariante 1).

    Nunca hace commit: la transacción la confirma el service. La empresa se carga
    siempre de forma explícita (joinedload): la relación es lazy="raise".
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, application: Application) -> Application:
        self.session.add(application)
        # flush envía el INSERT dentro de la transacción abierta: Postgres genera
        # id y fechas (server_default) y SQLAlchemy los lee con RETURNING.
        await self.session.flush()
        return application

    async def get(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application | None:
        return await self.session.scalar(
            select(Application)
            .options(joinedload(Application.company))
            .where(Application.user_id == user_id, Application.id == application_id)
            # Si la solicitud ya está en la sesión (p. ej. tras cambiar company_id),
            # refresca sus datos y su empresa en lugar de devolver la copia en memoria.
            .execution_options(populate_existing=True)
        )

    async def get_for_update(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application | None:
        """Como `get`, pero bloquea la fila (`SELECT … FOR UPDATE`) para serializar
        cambios de estado concurrentes (arquitectura §8). Sin `joinedload`: quien
        cambia de estado no necesita la empresa, y bloquear a través de un LEFT JOIN
        fallaría en Postgres si la relación fuera opcional.
        """
        return await self.session.scalar(
            select(Application)
            .where(Application.user_id == user_id, Application.id == application_id)
            .with_for_update()
        )

    async def count(self, user_id: uuid.UUID) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == user_id)
        )
        return total or 0

    async def list(
        self,
        user_id: uuid.UUID,
        filters: ApplicationFilters,
        *,
        page: int,
        limit: int,
        sort_by: ApplicationSort,
        descending: bool,
    ) -> tuple[list[Application], int]:
        query = self._filtered(user_id, filters)

        total = await self.session.scalar(
            select(func.count()).select_from(
                query.with_only_columns(Application.id).subquery()
            )
        )

        sort_column = {
            "applied_at": Application.applied_at,
            "created_at": Application.created_at,
            "updated_at": Application.updated_at,
            "company": func.lower(Company.name),
            "position_title": func.lower(Application.position_title),
        }[sort_by]
        # Las solicitudes guardadas no tienen applied_at: siempre al final, tanto
        # en orden ascendente como descendente. Desempate por id: orden estable.
        order = (sort_column.desc() if descending else sort_column.asc()).nulls_last()

        result = await self.session.scalars(
            # contains_eager: reutiliza el join de _filtered en vez de añadir otro.
            query.options(contains_eager(Application.company))
            .order_by(order, Application.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return list(result.all()), total or 0

    def _filtered(
        self, user_id: uuid.UUID, filters: ApplicationFilters
    ) -> Select[tuple[Application]]:
        # join (no solo joinedload) para poder filtrar y ordenar por el nombre de la
        # empresa. La condición incluye user_id, igual que la FK compuesta.
        query = (
            select(Application)
            .join(
                Company,
                (Company.id == Application.company_id)
                & (Company.user_id == Application.user_id),
            )
            .where(Application.user_id == user_id)
        )

        if filters.statuses:
            query = query.where(Application.status.in_(filters.statuses))
        if filters.company_id:
            query = query.where(Application.company_id == filters.company_id)
        if filters.work_modes:
            query = query.where(Application.work_mode.in_(filters.work_modes))
        if filters.sources:
            query = query.where(Application.source.in_(filters.sources))
        if filters.applied_from:
            query = query.where(Application.applied_at >= filters.applied_from)
        if filters.applied_to:
            query = query.where(Application.applied_at <= filters.applied_to)
        if filters.search:
            pattern = contains_pattern(filters.search)
            query = query.where(
                or_(
                    Application.position_title.ilike(pattern, escape=LIKE_ESCAPE),
                    Company.name.ilike(pattern, escape=LIKE_ESCAPE),
                )
            )
        if filters.archived is True:
            query = query.where(Application.archived_at.is_not(None))
        elif filters.archived is False:
            query = query.where(Application.archived_at.is_(None))

        return query

    async def save(self, application: Application) -> Application:
        """Envía a la BD los cambios de una solicitud ya cargada (UPDATE)."""
        await self.session.flush()
        return application

    async def delete(self, application: Application) -> None:
        await self.session.delete(application)
        await self.session.flush()

    # --- Dashboard (F5, RF-60…66) y exportación (RF-70) --------------------------

    async def count_by_status(
        self, user_id: uuid.UUID
    ) -> Sequence[Row[tuple[str, int]]]:
        """RF-60: recuento por estado, excluidas las archivadas."""
        result = await self.session.execute(
            select(Application.status, func.count())
            .where(Application.user_id == user_id, Application.archived_at.is_(None))
            .group_by(Application.status)
        )
        return result.all()

    async def applications_per_week(
        self, user_id: uuid.UUID, *, since: date
    ) -> Sequence[Row[tuple[datetime, int]]]:
        """RF-61: envíos agrupados por semana (incluye archivadas: es histórico, no
        una foto del estado actual)."""
        week_start = func.date_trunc("week", Application.applied_at)
        result = await self.session.execute(
            select(week_start, func.count())
            .where(Application.user_id == user_id, Application.applied_at >= since)
            .group_by(week_start)
        )
        return result.all()

    async def response_rate_counts(
        self, user_id: uuid.UUID, *, reached_statuses: Sequence[str]
    ) -> tuple[int, int]:
        """RF-62: (enviadas, que llegaron a `reached_statuses` o más allá). Incluye
        archivadas, igual que `applications_per_week`."""
        sent = select(Application.id).where(
            Application.user_id == user_id, Application.applied_at.is_not(None)
        )
        sent_count = await self.session.scalar(
            select(func.count()).select_from(sent.subquery())
        )

        reached = (
            select(Application.id)
            .join(
                ApplicationStatusChange,
                ApplicationStatusChange.application_id == Application.id,
            )
            .where(
                Application.user_id == user_id,
                Application.applied_at.is_not(None),
                ApplicationStatusChange.to_status.in_(reached_statuses),
            )
            .distinct()
        )
        reached_count = await self.session.scalar(
            select(func.count()).select_from(reached.subquery())
        )
        return sent_count or 0, reached_count or 0

    async def list_stale(
        self,
        user_id: uuid.UUID,
        *,
        statuses: Sequence[str],
        before: datetime,
        limit: int,
    ) -> tuple[Sequence[Application], int]:
        """RF-64: activas, en un estado "de espera" y sin actividad desde `before`,
        de la más a la menos desatendida.

        Anotado como `Sequence`, no `list`: dentro de esta clase, `list` a secas
        resolvería al método `list` de más arriba (Python evalúa las anotaciones en
        el espacio de nombres de la clase), no al tipo integrado.
        """
        query = (
            select(Application)
            .join(
                Company,
                (Company.id == Application.company_id)
                & (Company.user_id == Application.user_id),
            )
            .where(
                Application.user_id == user_id,
                Application.archived_at.is_(None),
                Application.status.in_(statuses),
                Application.last_activity_at < before,
            )
        )
        total = await self.session.scalar(
            select(func.count()).select_from(
                query.with_only_columns(Application.id).subquery()
            )
        )
        result = await self.session.scalars(
            query.options(contains_eager(Application.company))
            .order_by(Application.last_activity_at.asc(), Application.id)
            .limit(limit)
        )
        return list(result.all()), total or 0

    async def list_all(self, user_id: uuid.UUID) -> Sequence[Application]:
        """RF-70: todas las solicitudes del usuario, archivadas incluidas. La
        exportación es un volcado completo, no la vista filtrada del listado."""
        result = await self.session.scalars(
            select(Application)
            .options(joinedload(Application.company))
            .where(Application.user_id == user_id)
            .order_by(Application.created_at)
        )
        return result.all()
