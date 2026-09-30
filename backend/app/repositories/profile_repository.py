import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile


class ProfileRepository:
    """Acceso a `profiles`. Todo método recibe user_id y filtra por él (invariante 1).

    Nunca hace commit: la transacción la confirma el service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> Profile | None:
        return await self.session.scalar(
            select(Profile).where(Profile.user_id == user_id)
        )

    async def get_or_create(self, user_id: uuid.UUID) -> Profile:
        """El perfil del usuario, creándolo vacío si aún no existe. Idempotente.

        ON CONFLICT DO NOTHING: dos guardados simultáneos del primer perfil no
        fallan con la clave única de `user_id`; los dos leen la misma fila."""
        await self.session.execute(
            insert(Profile)
            .values(user_id=user_id)
            .on_conflict_do_nothing(index_elements=[Profile.user_id])
        )
        profile = await self.get(user_id)
        assert profile is not None
        return profile

    async def save(self, profile: Profile) -> Profile:
        """Envía a la BD los cambios de un perfil ya cargado (UPDATE)."""
        await self.session.flush()
        return profile
