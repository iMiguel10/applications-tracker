from app.core.config import Settings
from app.infra.email.base import (
    EmailDeliveryUnknownError,
    EmailDisabledError,
    EmailError,
    EmailNotSentError,
    EmailSender,
    OutgoingEmail,
)
from app.infra.email.disabled import DisabledEmailSender
from app.infra.email.smtp import SmtpEmailSender

__all__ = [
    "EmailDeliveryUnknownError",
    "EmailDisabledError",
    "EmailError",
    "EmailNotSentError",
    "EmailSender",
    "OutgoingEmail",
    "build_email_sender",
]


def build_email_sender(settings: Settings) -> EmailSender:
    """Elige la implementación según la configuración. Solo lo llaman quienes
    cablean (deps.py, el worker, los scripts), nunca un service."""
    if not settings.smtp_host:
        return DisabledEmailSender()
    assert settings.email_from is not None  # lo garantiza el validador de Settings
    return SmtpEmailSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        security=settings.smtp_security,
        username=settings.smtp_username,
        password=settings.smtp_password,
        sender=settings.email_from,
        timeout_seconds=settings.smtp_timeout_seconds,
    )
