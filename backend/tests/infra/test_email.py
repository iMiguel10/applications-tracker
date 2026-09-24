"""`EmailSender`: implementación SMTP contra un servidor falso y la desactivada.

La clasificación de fallos es la base de "nunca dos veces" (RF-87): lo que con
seguridad no salió se puede reintentar; lo ambiguo, no (segundo plano §4).
"""

import contextlib
import socket

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.infra.email import (
    EmailDeliveryUnknownError,
    EmailDisabledError,
    EmailNotSentError,
    OutgoingEmail,
    build_email_sender,
)
from app.infra.email.smtp import SmtpEmailSender, SmtpSecurity
from tests.infra.fake_smtp import Behavior, FakeSmtpServer

EMAIL = OutgoingEmail(
    to="ana@example.com",
    subject="Recordatorio: llamar a Acme",
    text="Texto plano",
    html="<p>Texto <strong>HTML</strong></p>",
    headers={"List-Unsubscribe": "<https://example.com/baja>"},
)


def make_sender(
    port: int,
    *,
    timeout: float = 5,
    security: SmtpSecurity = "none",
    username: str | None = None,
) -> SmtpEmailSender:
    return SmtpEmailSender(
        host="127.0.0.1",
        port=port,
        security=security,
        username=username,
        password="secreto" if username else None,
        sender="Applications Tracker <no-reply@example.com>",
        timeout_seconds=timeout,
    )


@pytest.mark.asyncio
async def test_accepted_email_is_multipart_with_headers() -> None:
    async with FakeSmtpServer() as server:
        await make_sender(server.port).send(EMAIL)

    [message] = server.messages
    assert message["To"] == "ana@example.com"
    assert message["From"] == "Applications Tracker <no-reply@example.com>"
    assert message["Subject"] == "Recordatorio: llamar a Acme"
    assert message["List-Unsubscribe"] == "<https://example.com/baja>"
    assert message["Message-ID"].endswith("@example.com>")
    assert message.get_content_type() == "multipart/alternative"
    parts = [part.get_content_type() for part in message.iter_parts()]
    assert parts == ["text/plain", "text/html"]


@pytest.mark.asyncio
async def test_text_only_email_is_not_multipart() -> None:
    async with FakeSmtpServer() as server:
        await make_sender(server.port).send(
            OutgoingEmail(to="ana@example.com", subject="Hola", text="Solo texto")
        )

    [message] = server.messages
    assert message.get_content_type() == "text/plain"


@pytest.mark.asyncio
async def test_unreachable_server_is_not_sent() -> None:
    # Un puerto que se acaba de liberar: nadie escucha en él.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    with pytest.raises(EmailNotSentError) as exc_info:
        await make_sender(port).send(EMAIL)
    assert not isinstance(exc_info.value, EmailDeliveryUnknownError)


@pytest.mark.asyncio
@pytest.mark.parametrize("behavior", ["reject_rcpt", "reject_data"])
async def test_explicit_rejection_is_not_sent(behavior: Behavior) -> None:
    """Un código de error del servidor, antes o al final de DATA, es un rechazo:
    el mensaje no se aceptó y reintentarlo no puede duplicarlo."""
    async with FakeSmtpServer(behavior) as server:
        with pytest.raises(EmailNotSentError):
            await make_sender(server.port).send(EMAIL)

    assert server.messages == []


@pytest.mark.asyncio
async def test_connection_lost_after_data_is_unknown() -> None:
    """B4: el mensaje llegó entero y la conexión se cortó sin respuesta final.
    Puede que el servidor lo aceptara: no se puede dar por no enviado."""
    async with FakeSmtpServer("drop_after_data") as server:
        with pytest.raises(EmailDeliveryUnknownError):
            await make_sender(server.port).send(EMAIL)


@pytest.mark.asyncio
async def test_server_that_never_greets_is_not_sent_rather_than_unknown() -> None:
    """B5 a nivel de infra: un timeout ANTES de DATA (aquí, esperando el saludo)
    no puede haber entregado nada, así que es un "no enviado" reintentable y no un
    resultado desconocido, que se perdería sin reintentar."""
    async with FakeSmtpServer("silent") as server:
        with pytest.raises(EmailNotSentError) as exc_info:
            await make_sender(server.port, timeout=0.5).send(EMAIL)

    assert not isinstance(exc_info.value, EmailDeliveryUnknownError)


@pytest.mark.asyncio
async def test_connection_lost_before_data_is_not_sent_rather_than_unknown() -> None:
    """Un corte antes de transmitir el mensaje (al enviar RCPT) es la frontera
    contraria a B4: con seguridad no salió nada."""
    async with FakeSmtpServer("drop_at_rcpt") as server:
        with pytest.raises(EmailNotSentError) as exc_info:
            await make_sender(server.port).send(EMAIL)

    assert not isinstance(exc_info.value, EmailDeliveryUnknownError)
    assert server.messages == []


LINE_BREAK_EMAILS = {
    "subject": OutgoingEmail(
        to="ana@example.com", subject="Hola\r\nBcc: victima@example.com", text="x"
    ),
    "to": OutgoingEmail(
        to="ana@example.com\r\nBcc: victima@example.com", subject="Hola", text="x"
    ),
    "header": OutgoingEmail(
        to="ana@example.com",
        subject="Hola",
        text="x",
        headers={"List-Unsubscribe": "<https://x>\r\nBcc: victima@example.com"},
    ),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("field", LINE_BREAK_EMAILS)
async def test_line_break_in_a_header_cannot_inject_a_recipient(field: str) -> None:
    """El título de un recordatorio (lo escribe el usuario) acabará en el asunto:
    un salto de línea no puede inyectar cabeceras ni destinatarios."""
    async with FakeSmtpServer() as server:
        # Rechazarlo o sanearlo, ambos valen aquí: la clasificación del error es
        # la prueba siguiente. Lo que no vale es que la inyección llegue.
        with contextlib.suppress(Exception):
            await make_sender(server.port).send(LINE_BREAK_EMAILS[field])

    assert [r for r in server.recipients if "victima" in r] == []
    assert [m for m in server.messages if m["Bcc"] is not None] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("field", LINE_BREAK_EMAILS)
async def test_line_break_in_a_header_is_classified_as_not_sent(field: str) -> None:
    """Contrato de `EmailSender`: todo fallo es un `EmailError` que dice si es
    seguro reintentar (segundo plano §4). Un error sin clasificar llegaría al
    trabajo de F12 como una excepción cualquiera, igual que el caso SMTPUTF8."""
    async with FakeSmtpServer() as server:
        with pytest.raises(EmailNotSentError):
            await make_sender(server.port).send(LINE_BREAK_EMAILS[field])


@pytest.mark.asyncio
async def test_timeout_after_data_is_unknown() -> None:
    async with FakeSmtpServer("hang_after_data") as server:
        with pytest.raises(EmailDeliveryUnknownError):
            await make_sender(server.port, timeout=0.5).send(EMAIL)


@pytest.mark.asyncio
@pytest.mark.parametrize("security", ["starttls", "tls"])
async def test_encryption_is_never_downgraded(security: SmtpSecurity) -> None:
    """Si se pide cifrado y el servidor no lo ofrece (o no habla TLS), no se envía
    en claro: falla sin transmitir nada. El caso bueno (TLS real) solo se puede
    comprobar contra un servidor de verdad, con send_test_email."""
    async with FakeSmtpServer() as server:
        with pytest.raises(EmailNotSentError):
            await make_sender(server.port, security=security, timeout=2).send(EMAIL)

    assert server.recipients == []
    assert server.messages == []


@pytest.mark.asyncio
async def test_login_required_but_not_offered_is_not_sent() -> None:
    async with FakeSmtpServer() as server:
        with pytest.raises(EmailNotSentError):
            await make_sender(server.port, username="usuario").send(EMAIL)

    assert server.messages == []


@pytest.mark.asyncio
async def test_non_ascii_recipient_uses_smtputf8() -> None:
    async with FakeSmtpServer(smtputf8=True) as server:
        await make_sender(server.port).send(
            OutgoingEmail(to="josé@example.com", subject="Hola", text="Texto")
        )

    assert server.recipients == ["josé@example.com"]
    assert len(server.messages) == 1


@pytest.mark.asyncio
async def test_non_ascii_recipient_without_smtputf8_is_not_sent() -> None:
    """Sin la extensión, la dirección no se puede transmitir: se clasifica como
    no enviado (y no se escapa como un error de codificación sin clasificar)."""
    async with FakeSmtpServer() as server:
        with pytest.raises(EmailNotSentError, match="SMTPUTF8"):
            await make_sender(server.port).send(
                OutgoingEmail(to="josé@example.com", subject="Hola", text="Texto")
            )

    assert server.recipients == []


@pytest.mark.asyncio
async def test_disabled_sender_fails_loudly() -> None:
    sender = build_email_sender(settings.model_copy(update={"smtp_host": None}))

    assert sender.enabled is False
    with pytest.raises(EmailDisabledError):
        await sender.send(EMAIL)


def test_builds_smtp_sender_when_configured() -> None:
    configured = settings.model_copy(
        update={"smtp_host": "mailpit", "email_from": "no-reply@example.com"}
    )

    sender = build_email_sender(configured)

    assert isinstance(sender, SmtpEmailSender)
    assert sender.enabled is True


def test_smtp_host_without_email_from_does_not_start() -> None:
    with pytest.raises(ValidationError, match="EMAIL_FROM"):
        Settings(smtp_host="mailpit", email_from=None)
