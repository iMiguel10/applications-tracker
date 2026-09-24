"""Envía un email de prueba con la configuración SMTP de esta instalación (RNF-34).

    docker compose exec api python -m app.scripts.send_test_email destinatario@example.com

Sirve para comprobar el SMTP al desplegar, sin esperar a que la aplicación
necesite enviar algo. En desarrollo, el email llega a Mailpit
(http://localhost:8025). Termina con código 0 si el servidor aceptó el mensaje y
con 1 si no, diciendo si es seguro volver a intentarlo.
"""

import argparse
import asyncio
import sys

from app.core.config import settings
from app.infra.email import (
    EmailDeliveryUnknownError,
    EmailDisabledError,
    EmailNotSentError,
    OutgoingEmail,
    build_email_sender,
)

TEXT = """Hola:

Este es un email de prueba de Applications Tracker. Si lo estás leyendo, la
configuración SMTP de esta instalación funciona.
"""

HTML = """<p>Hola:</p>
<p>Este es un email de prueba de <strong>Applications Tracker</strong>. Si lo
estás leyendo, la configuración SMTP de esta instalación funciona.</p>
"""


async def main(recipient: str) -> int:
    sender = build_email_sender(settings)
    email = OutgoingEmail(
        to=recipient,
        subject="Email de prueba de Applications Tracker",
        text=TEXT,
        html=HTML,
    )
    try:
        await sender.send(email)
    except EmailDisabledError:
        print("SMTP sin configurar: define SMTP_HOST y EMAIL_FROM.", file=sys.stderr)
        return 1
    except EmailDeliveryUnknownError as exc:
        print(f"Resultado desconocido, puede que haya salido: {exc}", file=sys.stderr)
        return 1
    except EmailNotSentError as exc:
        print(f"No se envió (es seguro reintentar): {exc}", file=sys.stderr)
        return 1

    print(
        f"Aceptado por {settings.smtp_host}:{settings.smtp_port} "
        f"({settings.smtp_security}) para {recipient}."
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("recipient", help="Dirección a la que enviar la prueba")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.recipient)))
