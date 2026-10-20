"""Cambia el email de una cuenta desde la administración (derecho de rectificación).

    docker compose exec api python -m app.scripts.change_email ana@example.com ana@nuevo.es
    docker compose exec -T api python -m app.scripts.change_email ana@example.com ana@nuevo.es --yes

La aplicación no deja cambiarlo a la persona: si te lo pide, lo cambias tú. Antes de
cambiar nada muestra los dos emails y pide confirmación (`--yes` la salta, para
lanzarlo sin terminal). El email nuevo queda verificado (lo das por bueno tú, como
al crear la cuenta con `create_user`). La contraseña, las sesiones abiertas y los
datos no cambian: la persona entra desde ese momento con el email nuevo.

Si la instalación envía emails, avisa a la dirección antigua: si el cambio no lo
pidió la titular, se entera al momento. Asegúrate antes de que la petición viene de
ella: quien controle el email nuevo podría quedarse con la cuenta pidiendo una
contraseña nueva.

Termina con 1 si no hay ninguna cuenta con el email actual, si otra cuenta ya usa
el nuevo o si el nuevo no tiene forma de email; con 2 si no se confirma.
"""

import argparse
import asyncio
import sys

from app.core.config import settings
from app.core.supertokens import init_supertokens
from app.db.session import async_session_factory
from app.infra.email import build_email_sender
from app.services.account_provisioning_service import (
    AccountExistsError,
    AccountNotFoundError,
    AccountProvisioningService,
    InvalidEmailError,
)


async def main(current_email: str, new_email: str) -> int:
    init_supertokens()
    async with async_session_factory() as session:
        service = AccountProvisioningService(session, build_email_sender(settings))
        try:
            notified = await service.change_email(current_email, new_email)
        except AccountNotFoundError:
            print(f"No hay ninguna cuenta con {current_email}.", file=sys.stderr)
            return 1
        except AccountExistsError:
            print(f"Ya hay otra cuenta con {new_email}.", file=sys.stderr)
            return 1
        except InvalidEmailError:
            print(f"{new_email} no es un email válido.", file=sys.stderr)
            return 1

    print(f"Email cambiado: {current_email} → {new_email}, ya verificado.")
    if notified:
        print(f"Se ha avisado del cambio a {current_email}.")
    else:
        print(
            "No se ha avisado a la dirección antigua (sin SMTP o el envío falló): "
            "díselo tú a la persona."
        )
    return 0


def _confirmed(current_email: str, new_email: str) -> bool:
    if not sys.stdin.isatty():
        print("Sin terminal para confirmar: añade --yes.", file=sys.stderr)
        return False
    answer = input(f"¿Cambiar {current_email} → {new_email}? Escribe s para seguir: ")
    return answer.strip().lower() in {"s", "si", "sí", "y", "yes"}


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("current_email")
    parser.add_argument("new_email")
    parser.add_argument(
        "--yes", action="store_true", help="no pedir confirmación (sin terminal)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse()
    current, new = args.current_email.strip(), args.new_email.strip()
    if not args.yes and not _confirmed(current, new):
        print("No se ha cambiado nada.", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(main(current, new)))
