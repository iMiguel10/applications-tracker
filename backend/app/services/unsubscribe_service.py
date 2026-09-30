import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.domain.notifications import NotificationKind
from app.domain.unsubscribe import PREFERENCE_FOR_KIND, verify_unsubscribe_token
from app.repositories.user_repository import UserRepository


class InvalidUnsubscribeTokenError(AppException):
    def __init__(self) -> None:
        super().__init__(
            "Invalid unsubscribe link",
            status_code=400,
            code="invalid_unsubscribe_token",
        )


class UnsubscribeService:
    """Baja de un tipo de aviso con el enlace del email, sin sesión (RF-85).

    Solo toca la preferencia de ese tipo y de ese usuario: el token no da acceso a
    nada más. Una cuenta que ya no existe responde igual que una que sí, para que el
    enlace no sirva para averiguar si una cuenta sigue viva.
    """

    def __init__(
        self, session: AsyncSession, secret: str = settings.app_secret
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.secret = secret

    def describe(self, token: str) -> NotificationKind:
        """El tipo de aviso del enlace, sin aplicar nada: lo que hace un GET, que un
        escáner de enlaces puede disparar sin que nadie haya pulsado (segundo plano
        §5)."""
        _, kind = self._verify(token)
        return kind

    async def unsubscribe(self, token: str) -> NotificationKind:
        user_id, kind = self._verify(token)
        user = await self.users.get_by_id(user_id)
        if user is not None:
            setattr(user, PREFERENCE_FOR_KIND[kind], False)
            await self.users.save(user)
            await self.session.commit()
        return kind

    def _verify(self, token: str) -> tuple[uuid.UUID, NotificationKind]:
        verified = verify_unsubscribe_token(token, self.secret)
        if verified is None:
            raise InvalidUnsubscribeTokenError()
        return verified
