"""Cómo salen los emails de SuperTokens y qué pasa al registrarse y al recuperar la
contraseña (autenticación §8). Solo cableado del SDK: el envío real lo hace el
`worker`."""

import logging
from collections.abc import Callable
from typing import Any

from supertokens_python.ingredients.emaildelivery.types import EmailDeliveryInterface
from supertokens_python.recipe.emailpassword.interfaces import (
    APIInterface,
    APIOptions,
    PasswordResetPostOkResult,
    SignUpPostOkResult,
)
from supertokens_python.recipe.emailpassword.types import (
    FormField,
    PasswordResetEmailTemplateVars,
)
from supertokens_python.recipe.emailverification.types import (
    VerificationEmailTemplateVars,
)
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.asyncio import revoke_all_sessions_for_user
from supertokens_python.supertokens import get_request_from_user_context

from app.domain.user import language_from_accept_language
from app.infra.queue import JobQueue, QueueUnavailableError
from app.jobs.auth_emails import SEND_PASSWORD_RESET_EMAIL, SEND_VERIFICATION_EMAIL

logger = logging.getLogger(__name__)

# Tiempo máximo del trabajo: el del cliente SMTP (30 s por defecto) más margen para
# pedir el email y el token al core.
AUTH_EMAIL_JOB_TIMEOUT_SECONDS = 60

JobQueueProvider = Callable[[], JobQueue]


async def _enqueue_auth_email(
    job_queue: JobQueueProvider | None,
    job: str,
    *,
    supertokens_user_id: str,
    tenant_id: str,
    user_context: dict[str, Any],
) -> None:
    """Encola un email de la cuenta con solo ids y el idioma de la petición.

    Nunca el enlace: SuperTokens lo entrega ya hecho, con el token dentro, y Valkey
    guarda los trabajos en disco (`appendonly`). El `worker` genera otro al enviar;
    el que se descarta aquí nunca sale del proceso y caduca solo.
    """
    if job_queue is None:
        # El worker inicializa el SDK para pedir datos al core, nunca para
        # atender /auth/*: si llega aquí, algo está mal cableado.
        raise RuntimeError("Este proceso no encola emails de SuperTokens")
    request = get_request_from_user_context(user_context)
    language = language_from_accept_language(
        request.get_header("accept-language") if request is not None else None
    )
    try:
        await job_queue().enqueue(
            job,
            timeout_seconds=AUTH_EMAIL_JOB_TIMEOUT_SECONDS,
            # Un intento: el usuario puede pedirlo otra vez (segundo plano §2).
            max_attempts=1,
            supertokens_user_id=supertokens_user_id,
            tenant_id=tenant_id,
            language_hint=language.value if language is not None else None,
        )
    except QueueUnavailableError:
        # La respuesta al usuario no cambia (en la recuperación, la misma exista o
        # no la cuenta, T9): no llega el email y puede volver a pedirlo.
        logger.error("No se pudo encolar %s de %s", job, supertokens_user_id)


class QueuedPasswordResetEmail(EmailDeliveryInterface[PasswordResetEmailTemplateVars]):
    """Sustituye la entrega por defecto de SuperTokens (que enviaría desde sus
    servidores) por un trabajo en nuestra cola."""

    def __init__(self, job_queue: JobQueueProvider | None) -> None:
        self._job_queue = job_queue

    async def send_email(
        self,
        template_vars: PasswordResetEmailTemplateVars,
        user_context: dict[str, Any],
    ) -> None:
        await _enqueue_auth_email(
            self._job_queue,
            SEND_PASSWORD_RESET_EMAIL,
            supertokens_user_id=template_vars.user.id,
            tenant_id=template_vars.tenant_id,
            user_context=user_context,
        )


class QueuedVerificationEmail(EmailDeliveryInterface[VerificationEmailTemplateVars]):
    """Igual que la recuperación, para el reenvío del email de verificación
    (`POST /auth/user/email/verify/token`)."""

    def __init__(self, job_queue: JobQueueProvider | None) -> None:
        self._job_queue = job_queue

    async def send_email(
        self,
        template_vars: VerificationEmailTemplateVars,
        user_context: dict[str, Any],
    ) -> None:
        await _enqueue_auth_email(
            self._job_queue,
            SEND_VERIFICATION_EMAIL,
            supertokens_user_id=template_vars.user.id,
            tenant_id=template_vars.tenant_id,
            user_context=user_context,
        )


def emailpassword_api_overrides(
    job_queue: JobQueueProvider | None,
) -> Callable[[APIInterface], APIInterface]:
    """Dos cambios en las rutas de email y contraseña del SDK:

    - **Registro:** encola el email de verificación (RF-05). Lo hace el backend y no
      el frontend, para que cualquier cliente de la API lo reciba igual.
    - **Recuperación:** al completarla se cierran TODAS las sesiones del usuario:
      si alguien le robó una, recuperar la contraseña tiene que echarlo. Un access
      token ya emitido sigue valiendo hasta 5 minutos (decisión 0002); lo que se
      corta es la renovación.
    """

    def override(original: APIInterface) -> APIInterface:
        original_sign_up_post = original.sign_up_post
        original_password_reset_post = original.password_reset_post

        async def sign_up_post(
            form_fields: list[FormField],
            tenant_id: str,
            session: SessionContainer | None,
            should_try_linking_with_session_user: bool | None,
            api_options: APIOptions,
            user_context: dict[str, Any],
        ) -> Any:
            result = await original_sign_up_post(
                form_fields,
                tenant_id,
                session,
                should_try_linking_with_session_user,
                api_options,
                user_context,
            )
            if isinstance(result, SignUpPostOkResult):
                await _enqueue_auth_email(
                    job_queue,
                    SEND_VERIFICATION_EMAIL,
                    supertokens_user_id=result.user.id,
                    tenant_id=tenant_id,
                    user_context=user_context,
                )
            return result

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

        original.sign_up_post = sign_up_post  # type: ignore[method-assign]
        original.password_reset_post = password_reset_post  # type: ignore[method-assign]
        return original

    return override
