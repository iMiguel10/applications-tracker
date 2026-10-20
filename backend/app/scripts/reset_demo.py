"""Deja la cuenta de demostración como nueva.

    docker compose exec api python -m app.scripts.reset_demo
    docker compose exec api python -m app.scripts.reset_demo --email demo@example.com --language en

Borra la cuenta (con todo lo que hayan creado los visitantes: solicitudes, ficheros,
claves de IA, cambios de contraseña…) y la crea de nuevo con el email verificado, la
contraseña de la variable DEMO_PASSWORD y los límites de `domain/demo.py`. Pensado
para programarse cada día; la primera vez crea la cuenta. Un visitante con la sesión
abierta la pierde. Termina con 1 si falta DEMO_PASSWORD.
"""

import argparse
import asyncio
import os
import sys

from app.core.config import settings
from app.core.supertokens import init_supertokens
from app.db.session import async_session_factory
from app.domain.user import Language
from app.infra.storage import LocalFileStorage
from app.services.demo_account_service import DemoAccountService

DEFAULT_EMAIL = "demo@example.com"


async def main(email: str, language: Language) -> int:
    password = os.environ.get("DEMO_PASSWORD", "")
    if not password:
        print("Falta la variable DEMO_PASSWORD.", file=sys.stderr)
        return 1
    init_supertokens()
    async with async_session_factory() as session:
        service = DemoAccountService(session, LocalFileStorage(settings.files_root))
        await service.reset(email, password, language)
    print(f"Cuenta de demostración {email} lista.")
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument(
        "--language", choices=[item.value for item in Language], default="es"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse()
    sys.exit(asyncio.run(main(args.email.strip(), Language(args.language))))
