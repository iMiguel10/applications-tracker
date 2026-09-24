"""`LocalFileStorage` sobre un directorio temporal por prueba (ficheros §3 y §8).

El disco local no necesita doble: la misma implementación que en producción,
apuntando a `tmp_path` (arquitectura de la v2 §6).
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.infra.storage import (
    FileTooLargeError,
    InvalidStorageKeyError,
    LocalFileStorage,
    StorageKeyNotFoundError,
)

KEY = "users/u-1/documents/d-1.pdf"


async def chunks(*parts: bytes) -> AsyncIterator[bytes]:
    for part in parts:
        yield part


async def read_all(storage: LocalFileStorage, key: str) -> bytes:
    return b"".join([chunk async for chunk in await storage.open(key)])


def leftover_temporaries(root: Path) -> list[Path]:
    return list((root / ".tmp").glob("*")) if (root / ".tmp").exists() else []


@pytest.mark.asyncio
async def test_put_and_open_round_trip(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    size = await storage.put(KEY, chunks(b"%PDF-", b"1.7 contenido"))

    assert size == len(b"%PDF-1.7 contenido")
    assert await read_all(storage, KEY) == b"%PDF-1.7 contenido"
    assert (tmp_path / KEY).is_file()
    assert leftover_temporaries(tmp_path) == []


@pytest.mark.asyncio
async def test_large_content_is_read_back_in_chunks(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    content = bytes(range(256)) * 1024  # 256 KiB: varios trozos de 64 KiB

    await storage.put(KEY, chunks(content))

    read = [chunk async for chunk in await storage.open(KEY)]
    assert len(read) > 1
    assert b"".join(read) == content


@pytest.mark.asyncio
async def test_put_replaces_an_existing_file(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    await storage.put(KEY, chunks(b"primera version"))

    await storage.put(KEY, chunks(b"segunda"))

    assert await read_all(storage, KEY) == b"segunda"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key",
    [
        "../fuera.pdf",  # D7
        "users/../../fuera.pdf",
        "/etc/passwd",  # absoluta
        "users//doble.pdf",
        "",
        ".tmp/robado.part",  # directorio de temporales
        "users/.oculto",
        "users\\u-1\\d.pdf",
        "users/u 1/d.pdf",
    ],
)
async def test_invalid_keys_are_rejected(tmp_path: Path, key: str) -> None:
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(InvalidStorageKeyError):
        await storage.put(key, chunks(b"x"))
    with pytest.raises(InvalidStorageKeyError):
        await storage.open(key)
    with pytest.raises(InvalidStorageKeyError):
        await storage.delete(key)


@pytest.mark.asyncio
async def test_symlink_pointing_outside_the_root_is_rejected(tmp_path: Path) -> None:
    """D7: una clave con forma válida que, resuelta, sale de la raíz."""
    root = tmp_path / "files"
    outside = tmp_path / "fuera"
    root.mkdir()
    outside.mkdir()
    (root / "users").symlink_to(outside, target_is_directory=True)
    storage = LocalFileStorage(root)

    with pytest.raises(InvalidStorageKeyError):
        await storage.put("users/escape.pdf", chunks(b"x"))
    assert list(outside.iterdir()) == []


@pytest.mark.asyncio
async def test_exceeding_max_bytes_writes_nothing(tmp_path: Path) -> None:
    """Base de D2: se cuenta mientras se escribe y no queda ni el fichero ni el
    temporal."""
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(FileTooLargeError):
        await storage.put(KEY, chunks(b"a" * 600, b"b" * 600), max_bytes=1000)

    assert not (tmp_path / KEY).exists()
    assert leftover_temporaries(tmp_path) == []


@pytest.mark.asyncio
async def test_content_exactly_at_the_limit_is_accepted(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    size = await storage.put(KEY, chunks(b"a" * 1000), max_bytes=1000)

    assert size == 1000


@pytest.mark.asyncio
async def test_failed_write_leaves_no_partial_file(tmp_path: Path) -> None:
    """Si la fuente falla a mitad (p. ej. se corta la subida), un lector nunca ve
    un fichero a medias: ni en su sitio ni como temporal."""
    storage = LocalFileStorage(tmp_path)
    await storage.put(KEY, chunks(b"version anterior completa"))

    async def broken() -> AsyncIterator[bytes]:
        yield b"trozo"
        raise ConnectionError("subida cortada")

    with pytest.raises(ConnectionError):
        await storage.put(KEY, broken())

    assert await read_all(storage, KEY) == b"version anterior completa"
    assert leftover_temporaries(tmp_path) == []


@pytest.mark.asyncio
async def test_open_missing_key_fails_on_call(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(StorageKeyNotFoundError):
        await storage.open(KEY)


@pytest.mark.asyncio
async def test_delete_is_idempotent(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    await storage.put(KEY, chunks(b"x"))

    await storage.delete(KEY)
    await storage.delete(KEY)

    assert not (tmp_path / KEY).exists()


@pytest.mark.asyncio
async def test_delete_prefix_removes_only_that_user(tmp_path: Path) -> None:
    """Base de D11: borrar la cuenta borra `users/{user_id}/` y nada más."""
    storage = LocalFileStorage(tmp_path)
    await storage.put("users/u-1/documents/a.pdf", chunks(b"a"))
    await storage.put("users/u-1/documents/b.pdf", chunks(b"b"))
    await storage.put("users/u-2/documents/c.pdf", chunks(b"c"))

    await storage.delete_prefix("users/u-1")
    await storage.delete_prefix("users/u-1")  # ya no existe: no falla

    assert not (tmp_path / "users/u-1").exists()
    assert await read_all(storage, "users/u-2/documents/c.pdf") == b"c"
