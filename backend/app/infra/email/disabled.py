from app.infra.email.base import EmailDisabledError, OutgoingEmail


class DisabledEmailSender:
    """El `EmailSender` de una instalación sin SMTP (RNF-34).

    Falla en voz alta en lugar de descartar el email en silencio: quien llame sin
    consultar `enabled` antes se entera, en vez de dar por enviado algo que no salió.
    """

    @property
    def enabled(self) -> bool:
        return False

    async def send(self, email: OutgoingEmail) -> None:
        raise EmailDisabledError("SMTP no configurado en esta instalación")
