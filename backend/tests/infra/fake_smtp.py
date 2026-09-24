"""Servidor SMTP mínimo para las pruebas de `SmtpEmailSender`.

Escrito a mano (y no con aiosmtpd) para poder fallar exactamente en el punto que
cada prueba necesita: rechazar el destinatario, rechazar el mensaje al final de
DATA, cortar la conexión con el mensaje ya recibido o no contestar nunca.
"""

import asyncio
from email import message_from_bytes, policy
from email.message import EmailMessage
from types import TracebackType
from typing import Literal, Self

Behavior = Literal[
    "accept",
    "reject_rcpt",
    "reject_data",
    "drop_after_data",
    "hang_after_data",
]


class FakeSmtpServer:
    def __init__(
        self, behavior: Behavior = "accept", *, smtputf8: bool = False
    ) -> None:
        self.behavior = behavior
        self.smtputf8 = smtputf8
        self.messages: list[EmailMessage] = []
        self.recipients: list[str] = []  # direcciones de sobre (RCPT TO)
        self.port = 0
        self._server: asyncio.Server | None = None
        self._handlers: set[asyncio.Task[None]] = set()

    async def __aenter__(self) -> Self:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._server is not None
        self._server.close()
        # Server.close() no corta las conexiones abiertas: se cancelan a mano para
        # que "hang_after_data" no deje una tarea colgada al cerrar el event loop.
        for task in self._handlers:
            task.cancel()
        await asyncio.gather(*self._handlers, return_exceptions=True)

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        assert task is not None
        self._handlers.add(task)

        def reply(line: str) -> None:
            writer.write(f"{line}\r\n".encode())

        reply("220 fake ESMTP")
        while line := await reader.readline():
            command = line[:4].upper()
            if command in (b"EHLO", b"HELO"):
                # Nunca anuncia STARTTLS ni AUTH; SMTPUTF8 solo si se pide.
                if self.smtputf8:
                    reply("250-fake")
                    reply("250 SMTPUTF8")
                else:
                    reply("250 fake")
            elif command == b"MAIL":
                reply("250 OK")
            elif command == b"RCPT":
                address = line.decode().split(":", 1)[1].split(">")[0].strip(" <")
                if self.behavior != "reject_rcpt":
                    self.recipients.append(address)
                reply(
                    "550 no such user" if self.behavior == "reject_rcpt" else "250 OK"
                )
            elif command == b"DATA":
                reply("354 go ahead")
                await writer.drain()
                data = await reader.readuntil(b"\r\n.\r\n")
                if self.behavior == "drop_after_data":
                    writer.close()
                    return
                if self.behavior == "hang_after_data":
                    await asyncio.sleep(3600)
                if self.behavior == "reject_data":
                    reply("554 rejected")
                else:
                    # policy.default: devuelve EmailMessage (con iter_parts), no el
                    # Message de compat32.
                    body = data[: -len(b".\r\n")]
                    self.messages.append(
                        message_from_bytes(body, policy=policy.default)
                    )
                    reply("250 queued")
            elif command == b"QUIT":
                reply("221 bye")
                await writer.drain()
                writer.close()
                return
            else:
                reply("502 not implemented")
            await writer.drain()
