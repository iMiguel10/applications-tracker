"""Crea una cuenta desde la administración (decisión 0022).

    docker compose exec api python -m app.scripts.create_user ana@example.com
    docker compose exec api python -m app.scripts.create_user ana@example.com --language en

Es la forma de dar de alta a alguien con el registro cerrado (SIGNUP_ENABLED=false),
y también funciona con el registro abierto. La cuenta nace con una contraseña
aleatoria que nadie ve y con el email ya verificado. La persona elige su contraseña
con un enlace: si hay SMTP, le llega por email; si no, o si el envío falla, el
script lo imprime para que se lo pases tú. El enlace caduca en 60 minutos; después
puede pedir otro con "¿Olvidaste tu contraseña?" (si hay correo).

Termina con 1 si ya existe una cuenta con ese email.
"""

import argparse
import asyncio
import sys

from app.core.config import settings
from app.core.supertokens import init_supertokens
from app.db.session import async_session_factory
from app.domain.user import Language
from app.infra.email import build_email_sender
from app.services.account_provisioning_service import (
    AccountExistsError,
    AccountProvisioningService,
)


async def main(email: str, language: Language | None) -> int:
    init_supertokens()
    async with async_session_factory() as session:
        service = AccountProvisioningService(session, build_email_sender(settings))
        try:
            created = await service.create(email, language)
        except AccountExistsError:
            print(f"Ya existe una cuenta con {email}.", file=sys.stderr)
            return 1

    print(f"Cuenta creada para {email}, con el email ya verificado.")
    if created.email_sent:
        print("Le ha llegado un email para que elija su contraseña.")
    else:
        print(
            "No se ha enviado ningún email (sin SMTP o el envío falló). Pásale este "
            "enlace para que elija su contraseña; caduca en 60 minutos:"
        )
        print(created.link)
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument(
        "--language",
        choices=[item.value for item in Language],
        help="idioma de la cuenta y del email (por defecto, el de la interfaz)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse()
    language = Language(args.language) if args.language else None
    sys.exit(asyncio.run(main(args.email.strip(), language)))
