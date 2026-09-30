import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents import user_prefix
from app.infra.storage import FileStorage
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser

logger = logging.getLogger(__name__)


class AccountService:
    """Borrado de la cuenta (RNF-40, RNF-41). Aparte de `UserService`, que se
    construye en cada petición autenticada: este toca tres sistemas (la BD, los
    ficheros y SuperTokens) y solo lo necesita `DELETE /me`."""

    def __init__(
        self,
        session: AsyncSession,
        storage: FileStorage,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.users = UserRepository(session)
        self.identities = identities or IdentityRepository()

    async def delete_account(self, current_user: CurrentUser) -> None:
        """Borra, en este orden:

        1. Los datos propios (en cascada desde `users`) y commit. Postgres manda.
        2. Sus ficheros (`users/{id}/`). Después del commit (RNF-41): un fichero
           huérfano lo limpia el barrido; una fila apuntando a un fichero borrado
           rompería la interfaz. Si falla, no se interrumpe el borrado.
        3. La identidad en SuperTokens. Un fallo aquí deja una identidad sin datos
           que puede volver a entrar y reintentarlo (arquitectura §4); se propaga
           para que el cliente no crea que la cuenta ya no existe.
        """
        await self.users.delete(current_user.id)
        await self.session.commit()
        try:
            await self.storage.delete_prefix(user_prefix(current_user.id))
        except Exception:
            logger.exception(
                "No se pudieron borrar los ficheros de la cuenta %s; los limpiará el "
                "barrido de huérfanos",
                current_user.id,
            )
        await self.identities.delete(current_user.supertokens_user_id)
