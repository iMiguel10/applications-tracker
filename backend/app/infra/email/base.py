from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class OutgoingEmail:
    """Un email listo para enviar. `text` es obligatorio y `html` opcional: un email
    solo HTML despierta más sospechas en los filtros de spam (segundo plano §5)."""

    to: str
    subject: str
    text: str
    html: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)


class EmailError(Exception):
    """Base de los errores de envío. Ninguno incluye credenciales del SMTP."""


class EmailNotSentError(EmailError):
    """Con seguridad NO salió: falló la conexión, TLS, la autenticación o el
    servidor lo rechazó con un código. Reintentarlo es seguro."""


class EmailDeliveryUnknownError(EmailError):
    """No se sabe si salió: la conexión se cortó o expiró mientras se transmitía
    el mensaje o se esperaba la respuesta final. Reintentarlo podría duplicarlo,
    así que no se reintenta (RF-87, segundo plano §4)."""


class EmailDisabledError(EmailNotSentError):
    """Esta instalación no tiene SMTP configurado (RNF-34)."""


class EmailSender(Protocol):
    """Envía un email o lanza un `EmailError` que dice si es seguro reintentarlo.

    `enabled` es False en una instalación sin SMTP: quien llama lo consulta para
    ofrecer (o no) las funciones que dependen del email.
    """

    @property
    def enabled(self) -> bool: ...

    async def send(self, email: OutgoingEmail) -> None: ...
