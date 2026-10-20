import io
import json
import logging
import zipfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.account_export import (
    EXPORTED_TABLES,
    FORMAT_VERSION,
    README_FILE,
    document_path,
    readme_text,
    table_file,
    to_json_value,
)
from app.domain.documents import DocumentStatus
from app.infra.storage import FileStorage, StorageKeyNotFoundError
from app.models.document import Document
from app.repositories.account_export_repository import AccountExportRepository
from app.repositories.identity_repository import IdentityRepository
from app.schemas.user import CurrentUser

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportedFile:
    """Un PDF de la cuenta: dónde va dentro del `.zip` y dónde está en el almacén."""

    path: str
    storage_key: str


@dataclass(frozen=True)
class AccountSnapshot:
    """Todo lo de la base de datos ya leído y convertido a JSON, y la lista de PDF
    que hay que copiar. Una vez hecha, el `.zip` se arma sin volver a la BD."""

    exported_at: datetime
    json_files: dict[str, Any]
    documents: list[ExportedFile]


def _row_to_json(row: Any, omitted: frozenset[str]) -> dict[str, Any]:
    """Todas las columnas de la fila salvo las omitidas, con el nombre de la columna
    en la BD: una columna nueva sale sola (portabilidad) salvo que se omita."""
    values: dict[str, Any] = {}
    for attribute in inspect(row).mapper.column_attrs:
        column = attribute.columns[0].name
        if column not in omitted:
            values[column] = to_json_value(getattr(row, attribute.key))
    return values


class _ChunkSink(io.RawIOBase):
    """Destino del `ZipFile`: guarda lo escrito hasta que se envía. No admite
    `seek`, así que `zipfile` escribe cada entrada con su descriptor de datos al
    final y nunca vuelve atrás: el `.zip` se puede enviar mientras se arma."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def writable(self) -> bool:
        return True

    def write(self, data: Any) -> int:
        chunk = bytes(data)
        self._chunks.append(chunk)
        return len(chunk)

    def drain(self) -> bytes:
        data = b"".join(self._chunks)
        self._chunks.clear()
        return data


def _entry(path: str, exported_at: datetime) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=exported_at.timetuple()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


class AccountExportService:
    """Exportación de todos los datos de una cuenta (issue #4, RGPD arts. 15 y 20).

    La lee entera y la suelta antes de que empiece la copia de los PDF: un `.zip`
    de cien megas no debe tener una conexión del pool ocupada mientras se descarga.
    La usan `GET /me/export` y `scripts/export_user.py`."""

    def __init__(
        self,
        session: AsyncSession,
        storage: FileStorage,
        identities: IdentityRepository | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.repository = AccountExportRepository(session)
        self.identities = identities or IdentityRepository()

    async def snapshot(
        self, current_user: CurrentUser, now: datetime | None = None
    ) -> AccountSnapshot:
        exported_at = now or datetime.now(UTC)
        user = await self.repository.user(current_user.id)
        if user is None:
            raise NotFoundError("User")
        # El email vive en SuperTokens (invariante 9): es el único dato de identidad
        # que se añade, el de la propia cuenta.
        email = await self.identities.get_email(current_user.supertokens_user_id)

        json_files: dict[str, Any] = {
            table_file("users"): {
                "format_version": FORMAT_VERSION,
                "exported_at": exported_at.isoformat(),
                "email": email,
                "account": _row_to_json(user, EXPORTED_TABLES["users"]),
            }
        }
        documents: list[ExportedFile] = []
        for table, omitted in EXPORTED_TABLES.items():
            if table == "users":
                continue
            rows = await self.repository.rows(table, current_user.id)
            json_files[table_file(table)] = [_row_to_json(row, omitted) for row in rows]
            if table == "documents":
                documents = [
                    ExportedFile(document_path(row.id, row.name), row.storage_key)
                    for row in rows
                    if isinstance(row, Document)
                    and row.status == DocumentStatus.READY
                    and row.storage_key
                ]

        # Solo lectura: el commit devuelve la conexión al pool antes de copiar los PDF.
        await self.session.commit()
        return AccountSnapshot(exported_at, json_files, documents)

    async def zip_stream(self, snapshot: AccountSnapshot) -> AsyncIterator[bytes]:
        """El `.zip` por trozos, sin guardarlo entero en memoria ni en disco: los
        JSON y después cada PDF leído del almacén por partes. Un PDF que ya no está
        (borrado mientras tanto) se omite y lo dice el README, que va el último."""
        sink = _ChunkSink()
        missing: list[str] = []
        with zipfile.ZipFile(sink, "w") as archive:
            for path, value in snapshot.json_files.items():
                archive.writestr(
                    _entry(path, snapshot.exported_at),
                    json.dumps(value, ensure_ascii=False, indent=2),
                )
                yield sink.drain()
            for document in snapshot.documents:
                # Se abre antes de crear la entrada: si no existe, no queda una a medias.
                try:
                    chunks = await self.storage.open(document.storage_key)
                except StorageKeyNotFoundError:
                    logger.warning(
                        "Exportación: falta el fichero %s", document.storage_key
                    )
                    missing.append(document.path)
                    continue
                with archive.open(
                    _entry(document.path, snapshot.exported_at), "w"
                ) as out:
                    async for chunk in chunks:
                        out.write(chunk)
                        yield sink.drain()
                yield sink.drain()
            archive.writestr(
                _entry(README_FILE, snapshot.exported_at),
                readme_text(snapshot.exported_at, missing),
            )
        # Al cerrarse, el ZipFile escribe el directorio central.
        yield sink.drain()
