import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import LegalNotConfiguredError, LegalVersionOutdatedError
from app.domain.legal import LEGAL_VERSION
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser, MeRead, PreferencesRead, PreferencesUpdate


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        identities: IdentityRepository | None = None,
        config: Settings = settings,
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.identities = identities or IdentityRepository()
        self.config = config

    async def get_or_create(self, supertokens_user_id: str) -> CurrentUser:
        user = await self.users.get_or_create(supertokens_user_id)
        # Solo hay algo que confirmar la primera vez; en el resto de peticiones la
        # transacción no ha escrito nada y el commit no cuesta.
        await self.session.commit()
        return CurrentUser(id=user.id, supertokens_user_id=user.supertokens_user_id)

    async def get_me(self, current_user: CurrentUser) -> MeRead:
        email = await self.identities.get_email(current_user.supertokens_user_id)
        user = await self.users.get_by_id(current_user.id)
        return MeRead(
            id=current_user.id,
            email=email,
            legal_accepted_version=user.legal_version if user else None,
        )

    async def accept_legal(
        self, user_id: uuid.UUID, version: str, now: datetime | None = None
    ) -> None:
        """Registra que la cuenta acepta los términos y la política de privacidad
        vigentes (issue #3): qué versión y cuándo. Solo la vigente: una pantalla
        abierta desde antes de un cambio de versión no acepta la anterior."""
        if not self.config.legal_configured:
            raise LegalNotConfiguredError()
        if version != LEGAL_VERSION:
            raise LegalVersionOutdatedError()
        user = await self.users.get_by_id(user_id)
        assert user is not None
        user.legal_version = version
        user.legal_accepted_at = now or datetime.now(UTC)
        await self.users.save(user)
        await self.session.commit()

    async def is_email_verified(self, supertokens_user_id: str) -> bool:
        return await self.identities.is_email_verified(supertokens_user_id)

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
