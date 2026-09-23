import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_supertokens_id(self, supertokens_user_id: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.supertokens_user_id == supertokens_user_id)
        )

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.scalar(select(User).where(User.id == user_id))

    async def save(self, user: User) -> User:
        """Envía a la BD los cambios de un usuario ya cargado (UPDATE)."""
        await self.session.flush()
        return user

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
