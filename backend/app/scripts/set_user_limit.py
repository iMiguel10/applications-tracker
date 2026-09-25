"""Consulta o cambia los límites de una cuenta concreta (RF-143).

    # Consumo y límites de la cuenta
    docker compose exec api python -m app.scripts.set_user_limit ana@example.com

    # Excepción: esta cuenta puede tener 10 000 solicitudes
    docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications 10000

    # Sin límite de solicitudes para esta cuenta
    docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications --unlimited

    # Sin límite en todo lo que lo admite
    docker compose exec api python -m app.scripts.set_user_limit ana@example.com all --unlimited

    # Quitar la excepción (o todas, con all): vuelve al valor global (LIMIT_*)
    docker compose exec api python -m app.scripts.set_user_limit ana@example.com applications --reset

La administración no tiene interfaz: este script es la única forma de ajustar un
límite individual. Rebajar un límite por debajo de lo ya creado no borra nada,
solo impide crear más. "Sin límite" solo existe para los límites que lo admiten:
los que protegen un recurso con coste (almacenamiento, IA) tienen tope siempre.
Termina con 1 si la cuenta no existe o el cambio no está permitido.
"""

import argparse
import asyncio
import sys
import uuid

from app.core.supertokens import init_supertokens
from app.db.session import async_session_factory
from app.domain.limits import LIMIT_RULES, LimitKey, keys_allowing_unlimited
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.services.limit_service import LimitService

ALL = "all"


async def _find_user(email: str) -> uuid.UUID | None:
    supertokens_id = await IdentityRepository().find_id_by_email(email)
    if supertokens_id is None:
        return None
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_supertokens_id(supertokens_id)
        return user.id if user is not None else None


async def _print_usage(user_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        for item in await LimitService(session).usage(user_id):
            source = "excepción" if item.overridden else "global"
            if item.limit is None:
                amounts = f"{item.used:>6} sin límite"
            else:
                amounts = (
                    f"{item.used:>6} de {item.limit:<6} quedan {item.remaining:<6}"
                )
            print(f"{item.key.value:<18} {amounts} ({source})")


async def _apply(
    user_id: uuid.UUID, keys: list[LimitKey], value: int | None, reset: bool
) -> None:
    async with async_session_factory() as session:
        service = LimitService(session)
        for key in keys:
            if reset:
                await service.clear_override(user_id, key)
            else:
                await service.set_override(user_id, key, value)


async def main(email: str, target: str | None, value: int | None, reset: bool) -> int:
    init_supertokens()
    user_id = await _find_user(email)
    if user_id is None:
        print(
            f"No hay ninguna cuenta con {email}, o aún no ha entrado en la aplicación.",
            file=sys.stderr,
        )
        return 1

    if target is not None:
        unlimited = value is None and not reset
        if target == ALL:
            # Con all, "sin límite" solo toca los límites que lo admiten; --reset,
            # todos.
            keys = keys_allowing_unlimited() if unlimited else list(LimitKey)
        else:
            keys = [LimitKey(target)]
            if unlimited and not LIMIT_RULES[keys[0]].allows_unlimited:
                print(
                    f"{target} protege un recurso con coste y tiene que tener un "
                    "límite: no admite --unlimited.",
                    file=sys.stderr,
                )
                return 1
        await _apply(user_id, keys, value, reset)

    await _print_usage(user_id)
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument(
        "limit", nargs="?", choices=[key.value for key in LimitKey] + [ALL]
    )
    parser.add_argument("value", nargs="?", type=int)
    parser.add_argument(
        "--unlimited", action="store_true", help="sin límite para esta cuenta"
    )
    parser.add_argument(
        "--reset", action="store_true", help="quita la excepción: vuelve al global"
    )
    args = parser.parse_args()
    chosen = sum([args.value is not None, args.unlimited, args.reset])
    if args.limit is None and chosen:
        parser.error("indica qué límite cambiar")
    if args.limit is not None and chosen == 0:
        parser.error(f"indica el nuevo valor de {args.limit}, --unlimited o --reset")
    if chosen > 1:
        parser.error("indica solo uno: un valor, --unlimited o --reset")
    if args.limit == ALL and args.value is not None:
        parser.error("con all solo se admite --unlimited o --reset")
    if args.value is not None and args.value < 0:
        parser.error("el límite no puede ser negativo")
    return args


if __name__ == "__main__":
    args = _parse()
    sys.exit(asyncio.run(main(args.email, args.limit, args.value, args.reset)))
