import logging
from datetime import UTC, datetime

from app.core.exceptions import (
    NotFoundError,
    PasswordPolicyError,
    WrongCurrentPasswordError,
)
from app.infra.queue import JobQueue, QueueUnavailableError
from app.repositories.identity_repository import IdentityRepository
from app.schemas.user import CurrentUser

logger = logging.getLogger(__name__)

# Trabajo del worker que envía el aviso (jobs/auth_emails.py). Un solo intento,
# como los demás emails de la cuenta: un reintento tras un fallo "no se sabe"
# podría duplicarlo (segundo plano §2).
SEND_PASSWORD_CHANGED_EMAIL = "send_password_changed_email"
PASSWORD_CHANGED_EMAIL_TIMEOUT_SECONDS = 60
# Más largo que esto no se manda al core: la política de SuperTokens no pasa de
# 100 caracteres, y así un cuerpo absurdo no llega a él.
PASSWORD_MAX_LENGTH = 256


class PasswordService:
    """Cambiar la contraseña con la actual (issue #2, decisión 0024).

    Pedir la actual protege de una sesión abierta en manos de otro, como antes lo
    hacía exigir el correo; y funciona también sin correo (RNF-34). La política de
    contraseñas la aplica SuperTokens, en el backend (invariante 7). No toca la
    base de datos de la aplicación: todo vive en el core."""

    def __init__(
        self,
        job_queue: JobQueue,
        *,
        email_enabled: bool,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.job_queue = job_queue
        self.email_enabled = email_enabled
        self.identities = identities or IdentityRepository()

    async def change(
        self,
        current_user: CurrentUser,
        *,
        session_handle: str,
        current_password: str,
        new_password: str,
    ) -> None:
        user_id = current_user.supertokens_user_id
        if len(current_password) > PASSWORD_MAX_LENGTH:
            raise WrongCurrentPasswordError()
        if len(new_password) > PASSWORD_MAX_LENGTH:
            raise PasswordPolicyError()
        email = await self.identities.get_email(user_id)
        if email is None:
            raise NotFoundError("User")
        if not await self.identities.verify_password(user_id, email, current_password):
            raise WrongCurrentPasswordError()
        if not await self.identities.update_password(user_id, new_password):
            raise PasswordPolicyError()
        # Como la recuperación, que cierra todas: aquí todas menos la de quien la
        # acaba de cambiar, que demostró conocer la anterior.
        await self.identities.revoke_other_sessions(user_id, session_handle)
        await self._notify(user_id, datetime.now(UTC))

    async def _notify(self, supertokens_user_id: str, changed_at: datetime) -> None:
        """El aviso por email de que la contraseña cambió: si no fue la persona de
        la cuenta, se entera y la recupera desde su correo. Sin correo no hay
        aviso. Si encolar falla, la contraseña ya está cambiada: se registra y no
        se convierte en un error (no hay barrido que lo reintente)."""
        if not self.email_enabled:
            return
        try:
            await self.job_queue.enqueue(
                SEND_PASSWORD_CHANGED_EMAIL,
                timeout_seconds=PASSWORD_CHANGED_EMAIL_TIMEOUT_SECONDS,
                max_attempts=1,
                supertokens_user_id=supertokens_user_id,
                changed_at=changed_at.isoformat(),
            )
        except QueueUnavailableError:
            logger.warning(
                "No se pudo encolar el aviso de contraseña cambiada de %s",
                supertokens_user_id,
            )
