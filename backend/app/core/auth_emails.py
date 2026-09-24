"""Cómo salen los emails de SuperTokens y qué pasa tras recuperar la contraseña
(autenticación §8). Solo cableado del SDK: el envío real lo hace el `worker`."""

import logging
from collections.abc import Callable
from typing import Any

from supertokens_python.ingredients.emaildelivery.types import EmailDeliveryInterface
from supertokens_python.recipe.emailpassword.interfaces import (
    APIInterface,
    APIOptions,
    PasswordResetPostOkResult,
)
from supertokens_python.recipe.emailpassword.types import (
    FormField,
    PasswordResetEmailTemplateVars,
)
from supertokens_python.recipe.session.asyncio import revoke_all_sessions_for_user
from supertokens_python.supertokens import get_request_from_user_context

from app.domain.user import language_from_accept_language
from app.infra.queue import JobQueue, QueueUnavailableError
from app.jobs.auth_emails import SEND_PASSWORD_RESET_EMAIL

logger = logging.getLogger(__name__)

# Tiempo máximo del trabajo: el del cliente SMTP (30 s por defecto) más margen para
# pedir el email y el token al core.
AUTH_EMAIL_JOB_TIMEOUT_SECONDS = 60


class QueuedPasswordResetEmail(EmailDeliveryInterface[PasswordResetEmailTemplateVars]):
    """Sustituye la entrega por defecto de SuperTokens (que enviaría desde sus
    servidores) por un trabajo en nuestra cola.

    El trabajo lleva solo ids: el enlace que SuperTokens ya ha generado se descarta
    y el `worker` genera otro al enviar. Así el token, que da acceso a la cuenta,
    no queda escrito en Valkey, que guarda los trabajos en disco (`appendonly`).
    El token descartado nunca sale de este proceso y caduca solo.
    """

    def __init__(self, job_queue: Callable[[], JobQueue] | None) -> None:
        self._job_queue = job_queue

    async def send_email(
        self,
        template_vars: PasswordResetEmailTemplateVars,
        user_context: dict[str, Any],
    ) -> None:
        if self._job_queue is None:
            # El worker inicializa el SDK para pedir datos al core, nunca para
            # atender /auth/*: si llega aquí, algo está mal cableado.
            raise RuntimeError("Este proceso no encola emails de SuperTokens")
        request = get_request_from_user_context(user_context)
        language = language_from_accept_language(
            request.get_header("accept-language") if request is not None else None
        )
        try:
            await self._job_queue().enqueue(
                SEND_PASSWORD_RESET_EMAIL,
                timeout_seconds=AUTH_EMAIL_JOB_TIMEOUT_SECONDS,
                # Un intento: el usuario puede pedirlo otra vez (segundo plano §2).
                max_attempts=1,
                supertokens_user_id=template_vars.user.id,
                tenant_id=template_vars.tenant_id,
                language_hint=language.value if language is not None else None,
            )
        except QueueUnavailableError:
            # La respuesta al usuario no cambia (la misma exista o no la cuenta, T9):
            # no llega el email y puede volver a pedirlo.
            logger.error(
                "No se pudo encolar la recuperación de %s", template_vars.user.id
            )


def revoke_sessions_after_password_reset(original: APIInterface) -> APIInterface:
    """Al recuperar la contraseña se cierran TODAS las sesiones del usuario: si
    alguien le robó una, recuperar la contraseña tiene que echarlo (autenticación
    §8). Un access token ya emitido sigue valiendo hasta 5 minutos (decisión 0002);
    lo que se corta es la renovación."""
    original_password_reset_post = original.password_reset_post

    async def password_reset_post(
        form_fields: list[FormField],
        token: str,
        tenant_id: str,
        api_options: APIOptions,
        user_context: dict[str, Any],
    ) -> Any:
        result = await original_password_reset_post(
            form_fields, token, tenant_id, api_options, user_context
        )
        if isinstance(result, PasswordResetPostOkResult):
            await revoke_all_sessions_for_user(
                result.user.id, user_context=user_context
            )
        return result

    original.password_reset_post = password_reset_post  # type: ignore[method-assign]
    return original
