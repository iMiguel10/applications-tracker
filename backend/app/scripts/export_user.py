"""Exporta todos los datos de una cuenta a un `.zip` (issue #4, RGPD arts. 15 y 20).

    docker compose exec -T api python -m app.scripts.export_user ana@example.com > ana.zip

Es el mismo `.zip` que la persona descarga en Preferencias (`GET /me/export`): para
cuando lo pide por otra vía (un email al responsable de la instalación) o ya no
puede entrar. Escribe el `.zip` en la salida estándar, así que redirígela a un
fichero (con `-T`: sin él, Docker mezcla la salida con un terminal y el `.zip` sale
roto); con `--output` lo escribe dentro del contenedor. Nunca lo escribe en un
terminal. Los mensajes van a la salida de errores.

Termina con 1 si no hay ninguna cuenta con ese email.
"""

import argparse
import asyncio
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.core.supertokens import init_supertokens
from app.db.session import async_session_factory
from app.infra.storage import LocalFileStorage
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.account_export_service import AccountExportService


async def main(email: str, output_path: Path | None) -> int:
    init_supertokens()
    identities = IdentityRepository()
    supertokens_user_id = await identities.find_id_by_email(email)
    async with async_session_factory() as session:
        user = (
            await UserRepository(session).get_by_supertokens_id(supertokens_user_id)
            if supertokens_user_id
            else None
        )
        if user is None or supertokens_user_id is None:
            print(f"No hay ninguna cuenta con {email}.", file=sys.stderr)
            return 1
        service = AccountExportService(
            session, LocalFileStorage(settings.files_root), identities
        )
        snapshot = await service.snapshot(
            CurrentUser(id=user.id, supertokens_user_id=supertokens_user_id)
        )
        size = 0
        target = output_path.open("wb") if output_path else nullcontext(_stdout())
        with target as output:
            async for chunk in service.zip_stream(snapshot):
                output.write(chunk)
                size += len(chunk)
            output.flush()

    print(
        f"Exportados los datos de {email}: {len(snapshot.documents)} PDF, "
        f"{size / 1024 / 1024:.1f} MB.",
        file=sys.stderr,
    )
    return 0


def _stdout() -> BinaryIO:
    return sys.stdout.buffer


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument(
        "--output",
        type=Path,
        help="fichero donde escribir el .zip (por defecto, la salida estándar)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse()
    if args.output is None and sys.stdout.isatty():
        print(
            "La salida es un terminal: redirígela a un fichero (> datos.zip) o usa "
            "--output.",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(asyncio.run(main(args.email.strip(), args.output)))
