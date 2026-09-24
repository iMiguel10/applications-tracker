"""Emails de la cuenta que dispara SuperTokens (autenticación §8)."""

from app.jobs.context import WorkerContext
from app.services.auth_email_service import AuthEmailService

SEND_PASSWORD_RESET_EMAIL = "send_password_reset_email"


async def send_password_reset_email(
    ctx: WorkerContext,
    *,
    supertokens_user_id: str,
    tenant_id: str,
    language_hint: str | None,
) -> None:
    async with ctx["session_factory"]() as session:
        service = AuthEmailService(session, email_sender=ctx["email_sender"])
        await service.send_password_reset(
            supertokens_user_id=supertokens_user_id,
            tenant_id=tenant_id,
            language_hint=language_hint,
        )
