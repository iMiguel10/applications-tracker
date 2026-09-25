import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.limits import LimitKey
from app.models.user_limit_override import UserLimitOverride


class UserLimitOverrideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID, key: LimitKey) -> UserLimitOverride | None:
        """La fila, no el valor: `value` None significa "sin límite", que no es lo
        mismo que no tener excepción."""
        return await self.session.scalar(
            select(UserLimitOverride).where(
                UserLimitOverride.user_id == user_id,
                UserLimitOverride.limit_key == key.value,
            )
        )

    async def get_all(self, user_id: uuid.UUID) -> dict[LimitKey, int | None]:
        """Solo las claves con excepción; su valor None es "sin límite"."""
        rows = await self.session.execute(
            select(UserLimitOverride.limit_key, UserLimitOverride.value).where(
                UserLimitOverride.user_id == user_id
            )
        )
        return {LimitKey(key): value for key, value in rows.tuples()}

    async def upsert(
        self, user_id: uuid.UUID, key: LimitKey, value: int | None
    ) -> None:
        statement = insert(UserLimitOverride).values(
            user_id=user_id, limit_key=key.value, value=value
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[UserLimitOverride.user_id, UserLimitOverride.limit_key],
                set_={"value": statement.excluded.value},
            )
        )

    async def delete(self, user_id: uuid.UUID, key: LimitKey) -> None:
        await self.session.execute(
            delete(UserLimitOverride).where(
                UserLimitOverride.user_id == user_id,
                UserLimitOverride.limit_key == key.value,
            )
        )
