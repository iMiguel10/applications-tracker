from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.demo import DEMO_LIMITS
from app.domain.user import Language
from app.infra.storage import FileStorage
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.account_service import AccountService
from app.services.limit_service import LimitService


class DemoAccountService:
    """Deja la cuenta de demostración como nueva (`scripts/reset_demo.py`).

    La contraseña es pública, así que nada de lo que haga un visitante debe
    sobrevivir: se borra la cuenta entera (datos, ficheros, claves de IA, sesiones e
    identidad, con `AccountService`) y se crea otra con la misma contraseña, el email
    verificado y los límites de `DEMO_LIMITS`. Los avisos por email quedan apagados:
    el dominio de la cuenta no recibe correo.
    """

    def __init__(
        self,
        session: AsyncSession,
        storage: FileStorage,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.session = session
        self.identities = identities or IdentityRepository()
        self.users = UserRepository(session)
        self.accounts = AccountService(session, storage, self.identities)
        self.limits = LimitService(session)

    async def reset(self, email: str, password: str, language: Language) -> None:
        old_id = await self.identities.find_id_by_email(email)
        if old_id is not None:
            user = await self.users.get_by_supertokens_id(old_id)
            if user is None:
                await self.identities.delete(old_id)
            else:
                await self.accounts.delete_account(
                    CurrentUser(id=user.id, supertokens_user_id=old_id)
                )

        supertokens_id = await self.identities.create_account(email, password)
        if supertokens_id is None:
            raise RuntimeError(f"No se pudo crear la cuenta {email}")
        await self.identities.mark_email_verified(supertokens_id, email)

        user = await self.users.get_or_create(supertokens_id)
        user.language = language
        user.notify_reminder_due = False
        user.notify_interview = False
        await self.users.save(user)
        await self.session.commit()

        for key, value in DEMO_LIMITS.items():
            await self.limits.set_override(user.id, key, value)
