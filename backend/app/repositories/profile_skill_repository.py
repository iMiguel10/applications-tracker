import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.profile_skill import ProfileLanguage, ProfileSkill


class ProfileSkillRepository:
    """Acceso a `profile_skills` y `profile_languages`. Tablas hijas de `profiles`:
    se filtra haciendo join con `profiles` para exigir `user_id` (invariante 1).

    Nunca hace commit: la transacción la confirma el service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def skills(self, user_id: uuid.UUID) -> Sequence[ProfileSkill]:
        result = await self.session.scalars(
            select(ProfileSkill)
            .join(Profile, Profile.id == ProfileSkill.profile_id)
            .where(Profile.user_id == user_id)
            .order_by(ProfileSkill.position, ProfileSkill.id)
        )
        return result.all()

    async def languages(self, user_id: uuid.UUID) -> Sequence[ProfileLanguage]:
        result = await self.session.scalars(
            select(ProfileLanguage)
            .join(Profile, Profile.id == ProfileLanguage.profile_id)
            .where(Profile.user_id == user_id)
            .order_by(ProfileLanguage.position, ProfileLanguage.id)
        )
        return result.all()

    def add(self, item: object) -> None:
        self.session.add(item)

    async def delete(self, item: object) -> None:
        await self.session.delete(item)

    async def flush(self) -> None:
        await self.session.flush()
