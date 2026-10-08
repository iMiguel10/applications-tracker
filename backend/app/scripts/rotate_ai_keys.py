"""Rota la clave maestra con que se cifran las claves de API de los usuarios
(ia.md §7).

    # 1. Generar una clave maestra nueva
    docker compose exec api python -m app.scripts.rotate_ai_keys --new-key

    # 2. Ponerla la PRIMERA en AI_KEYS_ENCRYPTION_KEYS (sin quitar las antiguas),
    #    recrear api y worker (--force-recreate) y volver a cifrar las guardadas:
    docker compose exec api python -m app.scripts.rotate_ai_keys

    # 3. Ya se puede quitar la antigua de AI_KEYS_ENCRYPTION_KEYS.

Con las antiguas aún en la lista, las claves se siguen descifrando durante la
rotación: no hay que parar nada. Termina con 1 si alguna clave no se pudo
descifrar con ninguna clave maestra (habría que pedir al usuario que la vuelva a
guardar); esas se dejan como están.
"""

import argparse
import asyncio
import sys

from app.core.config import settings
from app.db.session import async_session_factory
from app.infra.crypto import (
    KeyCipher,
    KeyCipherError,
    generate_master_key,
    parse_master_keys,
)
from app.repositories.ai_provider_key_repository import AiProviderKeyRepository

BATCH = 200


async def rotate() -> int:
    master_keys = parse_master_keys(settings.ai_keys_encryption_keys)
    if not master_keys:
        print("AI_KEYS_ENCRYPTION_KEYS está vacía: no hay nada que rotar.")
        return 1
    cipher = KeyCipher(master_keys)
    rotated = failed = 0
    after = None
    while True:
        # Una transacción por página: las filas quedan bloqueadas solo mientras se
        # vuelven a cifrar.
        async with async_session_factory() as session:
            keys = await AiProviderKeyRepository(session).all_for_rotation(BATCH, after)
            if not keys:
                break
            for key in keys:
                try:
                    key.ciphertext = cipher.rotate(key.ciphertext)
                    rotated += 1
                except KeyCipherError:
                    failed += 1
                    print(f"No se pudo descifrar la clave {key.id}", file=sys.stderr)
            after = keys[-1].id
            await session.commit()
    print(f"Claves cifradas de nuevo: {rotated}. Sin descifrar: {failed}.")
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--new-key",
        action="store_true",
        help="Solo muestra una clave maestra nueva para AI_KEYS_ENCRYPTION_KEYS.",
    )
    args = parser.parse_args()
    if args.new_key:
        print(generate_master_key())
        return
    sys.exit(asyncio.run(rotate()))


if __name__ == "__main__":
    main()
