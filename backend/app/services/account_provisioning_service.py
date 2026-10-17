import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import Language
from app.infra.email import EmailSender
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_email_service import AuthEmailService


@dataclass(frozen=True)
class CreatedAccount:
    user_id: uuid.UUID
    # True si el email de bienvenida salió; si no, `link` es el enlace para elegir
    # la contraseña, que quien administra pasa a mano.
    email_sent: bool
    link: str | None


class AccountExistsError(Exception):
    """Ya hay una cuenta con ese email."""


class AccountProvisioningService:
    """Crea cuentas desde la administración (`scripts/create_user.py`), la única
    forma de dar de alta a alguien con el registro cerrado (decisión 0022).

    La cuenta nace con una contraseña aleatoria que nadie ve y el email ya
    verificado (lo da por bueno quien la crea). La persona elige su contraseña con
    el enlace de recuperación: por email si hay SMTP, o a mano si no.
    """

    def __init__(
        self,
        session: AsyncSession,
        email_sender: EmailSender,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.identities = identities or IdentityRepository()
        self.emails = AuthEmailService(session, email_sender, self.identities)

    async def create(self, email: str, language: Language | None) -> CreatedAccount:
        supertokens_id = await self.identities.create_account(
            email, secrets.token_urlsafe(32)
        )
        if supertokens_id is None:
            raise AccountExistsError(email)
        await self.identities.mark_email_verified(supertokens_id, email)

        user = await self.users.get_or_create(supertokens_id)
        if language is not None:
            # Así el email de bienvenida y la interfaz salen en su idioma.
            user.language = language
            await self.users.save(user)
        await self.session.commit()

        sent = await self.emails.send_account_created(
            supertokens_user_id=supertokens_id, language_hint=None
        )
        link = (
            None
            if sent
            else await self.identities.create_password_reset_link(
                supertokens_id, email, "public"
            )
        )
        return CreatedAccount(user_id=user.id, email_sent=sent, link=link)
