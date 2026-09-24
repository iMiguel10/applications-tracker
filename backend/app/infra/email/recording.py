from app.infra.email.base import EmailError, OutgoingEmail


class RecordingEmailSender:
    """`EmailSender` de pruebas: guarda lo enviado y puede simular un fallo.

    Es parte del código y no un mock de cada test (servicios y estructura §8.7):
    ninguna prueba automática habla con un SMTP real.
    """

    def __init__(self, *, fail_with: EmailError | None = None) -> None:
        self.sent: list[OutgoingEmail] = []
        self.fail_with = fail_with

    @property
    def enabled(self) -> bool:
        return True

    async def send(self, email: OutgoingEmail) -> None:
        if self.fail_with is not None:
            raise self.fail_with
        self.sent.append(email)
