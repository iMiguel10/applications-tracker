import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@dataclass(frozen=True)
class DigestCandidate:
    user_id: uuid.UUID
    supertokens_user_id: str
    timezone: str | None
    created_at: datetime


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_supertokens_id(self, supertokens_user_id: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.supertokens_user_id == supertokens_user_id)
        )

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.scalar(select(User).where(User.id == user_id))

    async def lock(self, user_id: uuid.UUID) -> None:
        """Bloquea la fila del usuario hasta el final de la transacción (A30). Las
        cuotas con coste se comprueban con ella bloqueada: dos subidas simultáneas
        de la misma cuenta se ponen en fila en vez de pasarse juntas del límite."""
        await self.session.execute(
            select(User.id).where(User.id == user_id).with_for_update()
        )

    async def save(self, user: User) -> User:
        """Envía a la BD los cambios de un usuario ya cargado (UPDATE)."""
        await self.session.flush()
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        """Borra el usuario; sus datos caen con él por `ON DELETE CASCADE` (RNF-40)."""
        await self.session.execute(delete(User).where(User.id == user_id))

    async def get_or_create(self, supertokens_user_id: str) -> User:
        """Devuelve el usuario propio, creándolo si no existe. Idempotente.

        ON CONFLICT DO NOTHING hace que dos peticiones simultáneas del mismo
        usuario recién registrado no fallen: la segunda no inserta y ambas leen la
        misma fila (autenticacion.md, prueba T4).
        """
        existing = await self.get_by_supertokens_id(supertokens_user_id)
        if existing is not None:
            return existing

        await self.session.execute(
            insert(User)
            .values(supertokens_user_id=supertokens_user_id)
            .on_conflict_do_nothing(index_elements=[User.supertokens_user_id])
        )
        user = await self.get_by_supertokens_id(supertokens_user_id)
        assert user is not None
        return user

    async def list_for_digest(
        self, *, after: tuple[datetime, uuid.UUID] | None, limit: int
    ) -> Sequence[DigestCandidate]:
        """Usuarios con el resumen semanal activado (RF-82), paginados por
        `(created_at, id)`. La hora local se decide después, en Python: las zonas
        se validan con el tzdata de Python y Postgres podría no conocer algún nombre
        antiguo que da el navegador (A39).

        Recorre todos los usuarios a propósito: es un barrido del sistema."""
        query = select(
            User.id, User.supertokens_user_id, User.timezone, User.created_at
        ).where(User.notify_weekly_digest.is_(True))
        if after is not None:
            after_at, after_id = after
            query = query.where(
                or_(
                    User.created_at > after_at,
                    and_(User.created_at == after_at, User.id > after_id),
                )
            )
        rows = await self.session.execute(
            query.order_by(User.created_at, User.id).limit(limit)
        )
        return [DigestCandidate(*row) for row in rows.all()]
