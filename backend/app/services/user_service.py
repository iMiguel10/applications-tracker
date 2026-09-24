import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser, MeRead, PreferencesRead, PreferencesUpdate


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.identities = identities or IdentityRepository()

    async def get_or_create(self, supertokens_user_id: str) -> CurrentUser:
        user = await self.users.get_or_create(supertokens_user_id)
        # Solo hay algo que confirmar la primera vez; en el resto de peticiones la
        # transacción no ha escrito nada y el commit no cuesta.
        await self.session.commit()
        return CurrentUser(id=user.id, supertokens_user_id=user.supertokens_user_id)

    async def get_me(self, current_user: CurrentUser) -> MeRead:
        email = await self.identities.get_email(current_user.supertokens_user_id)
        return MeRead(id=current_user.id, email=email)

    async def get_preferences(self, user_id: uuid.UUID) -> PreferencesRead:
        # get_current_user ya crea la fila (invariante 8): si no existe, es un bug.
        user = await self.users.get_by_id(user_id)
        assert user is not None
        return PreferencesRead.model_validate(user)

    async def update_preferences(
        self, user_id: uuid.UUID, data: PreferencesUpdate
    ) -> PreferencesRead:
        user = await self.users.get_by_id(user_id)
        assert user is not None
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(user, field, value)
        await self.users.save(user)
        await self.session.commit()
        return PreferencesRead.model_validate(user)

    async def delete_account(self, current_user: CurrentUser) -> None:
        """Borra todos los datos propios y después la identidad en SuperTokens
        (arquitectura §4). En este orden, un fallo a mitad deja una identidad sin
        datos, que puede volver a entrar y reintentarlo; al revés quedarían datos
        huérfanos que nadie podría reclamar ni borrar."""
        await self.users.delete(current_user.id)
        await self.session.commit()
        await self.identities.delete(current_user.supertokens_user_id)
