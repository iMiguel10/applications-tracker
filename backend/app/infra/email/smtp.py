from email import policy
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from typing import Literal

import aiosmtplib

from app.infra.email.base import (
    EmailDeliveryUnknownError,
    EmailNotSentError,
    OutgoingEmail,
)

SmtpSecurity = Literal["none", "starttls", "tls"]


class SmtpEmailSender:
    """Envío por SMTP con `aiosmtplib`, clasificando **dónde** falla cada envío.

    La conversación se hace paso a paso (conexión y login, MAIL, RCPT, DATA) en
    lugar de con `send_message`, porque la frontera que importa está dentro de
    DATA: lo que falla antes de transmitir el mensaje no salió, y un corte
    mientras se transmite o se espera la respuesta final es ambiguo. Un código de
    error del servidor en cualquier punto es un rechazo explícito: no salió.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        security: SmtpSecurity,
        username: str | None,
        password: str | None,
        sender: str,
        timeout_seconds: float,
    ) -> None:
        self._host = host
        self._port = port
        self._security = security
        # Una variable vacía en el .env (SMTP_USERNAME=) significa "sin login".
        self._username = username or None
        self._password = password or None
        self._sender = sender
        self._envelope_sender = parseaddr(sender)[1]
        self._timeout = timeout_seconds

    @property
    def enabled(self) -> bool:
        return True

    async def send(self, email: OutgoingEmail) -> None:
        message = self._build_message(email)

        client = aiosmtplib.SMTP(
            hostname=self._host,
            port=self._port,
            use_tls=self._security == "tls",
            # False explícito: con None, aiosmtplib intenta STARTTLS por su cuenta
            # si el servidor lo anuncia, y "none" dejaría de significar "none".
            start_tls=self._security == "starttls",
            username=self._username,
            password=self._password,
            timeout=self._timeout,
        )

        # Direcciones con caracteres no ASCII (josé@…) solo viajan con la extensión
        # SMTPUTF8 (RFC 6531), y el mensaje se serializa entonces en UTF-8.
        needs_utf8 = not (email.to.isascii() and self._envelope_sender.isascii())
        options = ["SMTPUTF8"] if needs_utf8 else []
        encoding = "utf-8" if needs_utf8 else "ascii"

        try:
            await client.connect()
            # aiosmtplib saluda (EHLO) de forma perezosa, en el primer comando: sin
            # login ni STARTTLS, justo tras conectar aún no conoce las extensiones
            # del servidor y supports_extension diría que no a todo.
            if client.last_ehlo_response is None:
                await client.ehlo()
            if needs_utf8 and not client.supports_extension("smtputf8"):
                raise aiosmtplib.SMTPNotSupported(
                    "el servidor no admite direcciones con caracteres no ASCII (SMTPUTF8)"
                )
            await client.mail(self._envelope_sender, options=options, encoding=encoding)
            await client.rcpt(email.to, encoding=encoding)
        except (aiosmtplib.SMTPException, OSError) as exc:
            client.close()
            raise EmailNotSentError(_describe(exc)) from exc

        try:
            await client.data(
                message.as_bytes(policy=policy.SMTPUTF8 if needs_utf8 else policy.SMTP)
            )
        except aiosmtplib.SMTPResponseException as exc:
            # El servidor contestó con un código de error, al pedir DATA o al
            # final del mensaje: lo rechazó de forma explícita.
            client.close()
            raise EmailNotSentError(_describe(exc)) from exc
        except (aiosmtplib.SMTPException, OSError) as exc:
            # Corte o timeout con el mensaje en vuelo: puede que el servidor lo
            # aceptara y la confirmación no llegara.
            client.close()
            raise EmailDeliveryUnknownError(_describe(exc)) from exc

        # Entregado. Un fallo al despedirse ya no cambia nada.
        try:
            await client.quit()
        except (aiosmtplib.SMTPException, OSError):
            client.close()

    def _build_message(self, email: OutgoingEmail) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = email.to
        message["Subject"] = email.subject
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = make_msgid(domain=self._envelope_sender.split("@")[-1])
        for name, value in email.headers.items():
            message[name] = value
        message.set_content(email.text)
        if email.html is not None:
            message.add_alternative(email.html, subtype="html")
        return message


def _describe(exc: Exception) -> str:
    # Solo el tipo y el mensaje del servidor: nunca la configuración, que lleva
    # la contraseña del SMTP.
    return f"{type(exc).__name__}: {exc}"
