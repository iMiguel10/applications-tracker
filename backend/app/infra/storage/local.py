import asyncio
import os
import re
import shutil
import uuid
from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path
from typing import BinaryIO

from app.infra.storage.base import (
    FileTooLargeError,
    InvalidStorageKeyError,
    StorageKeyNotFoundError,
)

CHUNK_SIZE = 64 * 1024

# Cada segmento de una clave: letras, dígitos, punto, guion y guion bajo, sin
# empezar por punto. Deja fuera "..", ".", segmentos vacíos (claves absolutas o
# con "//"), barras invertidas y el directorio de temporales.
_SEGMENT = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._-]*")

# Temporales de escritura. DENTRO de la raíz a propósito: os.replace solo es
# atómico en el mismo sistema de ficheros (ficheros §3). Empieza por punto, así
# que ninguna clave válida puede apuntar aquí.
_TMP_DIR = ".tmp"


class LocalFileStorage:
    """`FileStorage` en disco local, sobre el volumen compartido por api y worker (A21).

    Todo el I/O de disco va a un hilo (`asyncio.to_thread`) para no bloquear el
    event loop mientras se escribe o se lee un fichero.
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()

    async def put(
        self,
        key: str,
        chunks: AsyncIterable[bytes],
        *,
        max_bytes: int | None = None,
    ) -> int:
        destination = self._resolve(key)
        temporary = self._root / _TMP_DIR / f"{uuid.uuid4()}.part"
        await asyncio.to_thread(temporary.parent.mkdir, parents=True, exist_ok=True)

        size = 0
        try:
            handle = await asyncio.to_thread(temporary.open, "wb")
            try:
                async for chunk in chunks:
                    size += len(chunk)
                    # Se cuenta lo que llega de verdad, no lo que se declaró
                    # (Content-Length puede mentir): se corta al pasarse.
                    if max_bytes is not None and size > max_bytes:
                        raise FileTooLargeError(f"más de {max_bytes} bytes")
                    await asyncio.to_thread(handle.write, chunk)
                await asyncio.to_thread(_flush_to_disk, handle)
            finally:
                await asyncio.to_thread(handle.close)
            await asyncio.to_thread(_move_into_place, temporary, destination)
        except BaseException:
            # También ante una cancelación (cliente que se desconecta a mitad de
            # una subida). Síncrono a propósito: un await aquí podría volver a
            # cancelarse y dejar el temporal.
            temporary.unlink(missing_ok=True)
            raise
        return size

    async def open(self, key: str) -> AsyncIterator[bytes]:
        path = self._resolve(key)
        try:
            handle = await asyncio.to_thread(path.open, "rb")
        except (FileNotFoundError, IsADirectoryError) as exc:
            raise StorageKeyNotFoundError(key) from exc
        return _read_chunks(handle)

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    async def delete_prefix(self, prefix: str) -> None:
        path = self._resolve(prefix.rstrip("/"))
        await asyncio.to_thread(_remove_tree, path)

    def _resolve(self, key: str) -> Path:
        """Ruta absoluta de `key`, o InvalidStorageKeyError si no es válida o si,
        resuelta, sale de la raíz. Lo segundo cubre también un enlace simbólico
        dentro del almacén que apunte fuera (A23)."""
        if not all(_SEGMENT.fullmatch(segment) for segment in key.split("/")):
            raise InvalidStorageKeyError(key)
        path = (self._root / key).resolve()
        if path == self._root or not path.is_relative_to(self._root):
            raise InvalidStorageKeyError(key)
        return path


async def _read_chunks(handle: BinaryIO) -> AsyncIterator[bytes]:
    # El fichero se cierra al terminar de leer o si quien consume se detiene
    # (StreamingResponse llama a aclose() cuando el cliente se desconecta).
    try:
        while chunk := await asyncio.to_thread(handle.read, CHUNK_SIZE):
            yield chunk
    finally:
        handle.close()


def _flush_to_disk(handle: BinaryIO) -> None:
    # Sin fsync, un corte de luz justo después del rename podría dejar el
    # fichero con su nombre definitivo pero vacío o incompleto.
    handle.flush()
    os.fsync(handle.fileno())


def _move_into_place(temporary: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temporary, destination)


def _remove_tree(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)
