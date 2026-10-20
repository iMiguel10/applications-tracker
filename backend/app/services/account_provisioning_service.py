import secrets
import uuid
from dataclasses import dataclass

from pydantic import EmailStr, TypeAdapter, ValidationError
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


class AccountNotFoundError(Exception):
    """No hay ninguna cuenta con ese email."""


class InvalidEmailError(Exception):
    """El email nuevo no tiene forma de email."""


_EMAIL = TypeAdapter(EmailStr)


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

    async def change_email(self, current_email: str, new_email: str) -> bool:
        """Cambia el email de una cuenta desde la administración (`scripts/
        change_email.py`, derecho de rectificación): la aplicación no deja hacerlo a
        la persona. El nuevo queda verificado, como al crear la cuenta: lo da por
        bueno quien administra. La contraseña y las sesiones no cambian.

        Con correo, avisa a la dirección antigua: si el nuevo no es de la titular
        (una errata, alguien que se hace pasar por ella), se entera al momento.
        Devuelve si ese aviso salió."""
        try:
            _EMAIL.validate_python(new_email)
        except ValidationError:
            raise InvalidEmailError(new_email) from None
        supertokens_id = await self.identities.find_id_by_email(current_email)
        if supertokens_id is None:
            raise AccountNotFoundError(current_email)
        # La que guarda el core, tal cual: el aviso va ahí.
        old_email = await self.identities.get_email(supertokens_id) or current_email
        if not await self.identities.update_email(supertokens_id, new_email):
            raise AccountExistsError(new_email)
        await self.identities.mark_email_verified(supertokens_id, new_email)
        return await self.emails.send_email_changed(
            supertokens_user_id=supertokens_id,
            old_email=old_email,
            new_email=new_email,
        )
