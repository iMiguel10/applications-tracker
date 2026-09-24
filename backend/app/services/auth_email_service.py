import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import DEFAULT_LANGUAGE, Language
from app.infra.email import (
    EmailDeliveryUnknownError,
    EmailDisabledError,
    EmailNotSentError,
    EmailSender,
    OutgoingEmail,
)
from app.infra.email.templates import EmailTemplates
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Vida del token de recuperación en el core (`password_reset_token_lifetime`, 1 h
# por defecto). Solo se usa para decirlo en el email: si se cambia en el core, se
# cambia aquí.
PASSWORD_RESET_LINK_MINUTES = 60


class AuthEmailService:
    """Emails de la cuenta que dispara SuperTokens (autenticación §8). Los ejecuta
    el `worker`: la API solo encola ids, y el enlace con el token se genera aquí,
    al enviar, para que el token no quede guardado en Valkey."""

    def __init__(
        self,
        session: AsyncSession,
        email_sender: EmailSender,
        identities: IdentityRepository | None = None,
        templates: EmailTemplates | None = None,
    ) -> None:
        self.users = UserRepository(session)
        self.email_sender = email_sender
        self.identities = identities or IdentityRepository()
        self.templates = templates or EmailTemplates()

    async def send_password_reset(
        self, *, supertokens_user_id: str, tenant_id: str, language_hint: str | None
    ) -> None:
        if not self.email_sender.enabled:
            # Sin SMTP no se genera ni el token: nadie lo recibiría (RNF-34).
            logger.warning("Recuperación de contraseña pedida sin SMTP configurado")
            return
        email = await self.identities.get_email(supertokens_user_id)
        if email is None:
            logger.info("Recuperación para un usuario que ya no existe; se ignora")
            return
        link = await self.identities.create_password_reset_link(
            supertokens_user_id, email, tenant_id
        )
        if link is None:
            logger.info("Recuperación para un usuario que ya no existe; se ignora")
            return

        language = await self._language_for(supertokens_user_id, language_hint)
        rendered = self.templates.render(
            "password_reset",
            language,
            {"link": link, "expires_in_minutes": PASSWORD_RESET_LINK_MINUTES},
        )
        await self._send(
            OutgoingEmail(
                to=email,
                subject=rendered.subject,
                text=rendered.text,
                html=rendered.html,
            ),
            kind="password_reset",
            supertokens_user_id=supertokens_user_id,
        )

    async def _language_for(
        self, supertokens_user_id: str, language_hint: str | None
    ) -> Language:
        """El idioma de la cuenta; si no lo fijó, el del navegador que lo pidió; y si
        tampoco, el de por defecto. El mismo orden que sigue la interfaz."""
        user = await self.users.get_by_supertokens_id(supertokens_user_id)
        if user is not None and user.language is not None:
            return Language(user.language)
        if language_hint is not None and language_hint in Language._value2member_map_:
            return Language(language_hint)
        return DEFAULT_LANGUAGE

    async def _send(
        self, email: OutgoingEmail, *, kind: str, supertokens_user_id: str
    ) -> None:
        # Un solo intento (segundo plano §2): el usuario puede volver a pedirlo, y
        # un reintento tras un fallo "no se sabe" podría duplicar el email. Los
        # registros llevan el id, no la dirección.
        try:
            await self.email_sender.send(email)
        except EmailDisabledError:
            logger.warning("Email %s no enviado: sin SMTP configurado", kind)
        except EmailDeliveryUnknownError:
            logger.warning(
                "Email %s a %s: no se sabe si salió", kind, supertokens_user_id
            )
        except EmailNotSentError:
            logger.warning(
                "Email %s a %s no enviado", kind, supertokens_user_id, exc_info=True
            )
        else:
            logger.info("Email %s enviado a %s", kind, supertokens_user_id)
