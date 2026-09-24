from collections.abc import AsyncIterable, AsyncIterator
from typing import Protocol


class StorageError(Exception):
    """Base de los errores del almacén."""


class InvalidStorageKeyError(StorageError):
    """La clave no es válida o, resuelta, saldría de la raíz del almacén (A23)."""


class StorageKeyNotFoundError(StorageError):
    """No hay ningún fichero con esa clave."""


class FileTooLargeError(StorageError):
    """El contenido superó `max_bytes` mientras se escribía. No queda nada escrito."""


class FileStorage(Protocol):
    """Almacén de ficheros por clave. Solo sabe de claves y bytes: la propiedad,
    las cuotas y los estados de un documento los decide el service (ficheros §1).

    Las claves las genera siempre el servidor (`users/{user_id}/documents/{id}.pdf`),
    relativas a la raíz, con segmentos de `[A-Za-z0-9._-]` que no empiezan por punto.
    """

    async def put(
        self,
        key: str,
        chunks: AsyncIterable[bytes],
        *,
        max_bytes: int | None = None,
    ) -> int:
        """Escribe el contenido de forma atómica y devuelve su tamaño real en bytes.
        Un lector nunca ve el fichero a medias; si ya existía, se sustituye entero.
        Con `max_bytes`, corta en cuanto se pasa (FileTooLargeError)."""
        ...

    async def open(self, key: str) -> AsyncIterator[bytes]:
        """Devuelve el contenido por trozos. StorageKeyNotFoundError si no existe
        (se comprueba al llamar, no al empezar a iterar)."""
        ...

    async def delete(self, key: str) -> None:
        """Borra el fichero. No falla si ya no existe."""
        ...

    async def delete_prefix(self, prefix: str) -> None:
        """Borra todo lo que cuelga de `prefix` (p. ej. `users/{user_id}`, sin barra
        final). No falla si no existe."""
        ...
