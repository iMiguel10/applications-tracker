import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileRead, ProfileUpdate


class ProfileService:
    """Perfil profesional (RF-100…102). Dueño de la transacción: es quien hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = ProfileRepository(session)

    async def get(self, user_id: uuid.UUID) -> ProfileRead:
        """Sin fila, el perfil existe vacío: leerlo no crea nada."""
        profile = await self.profiles.get(user_id)
        if profile is None:
            return ProfileRead()
        return ProfileRead.model_validate(profile)

    async def update(self, user_id: uuid.UUID, data: ProfileUpdate) -> ProfileRead:
        profile = await self.profiles.get_or_create(user_id)
        fields = data.model_dump(mode="json")
        for field, value in fields.items():
            setattr(profile, field, value)
        await self.profiles.save(profile)
        await self.session.commit()
        return ProfileRead.model_validate(profile)
