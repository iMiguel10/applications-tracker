import hashlib
import logging
import uuid
from collections.abc import AsyncIterable, AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import (
    ConflictError,
    DocumentInUseError,
    FileTooLargeAppError,
    InvalidFileTypeError,
    NotFoundError,
)
from app.domain.documents import (
    PDF_INSPECT_TIMEOUT_SECONDS,
    DocumentKind,
    DocumentOrigin,
    DocumentStatus,
    sanitize_name,
    storage_key,
)
from app.domain.limits import LimitKey
from app.infra.pdf.inspect import InvalidPdfError, count_pages
from app.infra.storage import FileStorage, StorageKeyNotFoundError
from app.models.document import Document
from app.repositories.application_repository import ApplicationRepository
from app.repositories.document_repository import DocumentFilters, DocumentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.document import DocumentListQuery
from app.services.limit_service import LimitService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentUsage:
    application_id: uuid.UUID
    position_title: str
    company_name: str
    used_as: DocumentKind
    application_archived: bool


class DocumentService:
    """Biblioteca de documentos (RF-90…94, ficheros §2).

    Postgres manda (invariante 9 de v2): el fichero se escribe ANTES de confirmar su
    fila. Si algo falla entre medias, sobra un fichero (que limpia el barrido de
    huérfanos), nunca falta uno al que apunte una fila.
    """

    def __init__(
        self,
        session: AsyncSession,
        storage: FileStorage,
        config: Settings = settings,
    ) -> None:
        self.session = session
        self.storage = storage
        self.config = config
        self.documents = DocumentRepository(session)
        self.applications = ApplicationRepository(session)
        self.users = UserRepository(session)
        self.limits = LimitService(session, config)

    async def list(
        self, user_id: uuid.UUID, query: DocumentListQuery
    ) -> tuple[Sequence[tuple[Document, int]], int]:
        """Cada documento con en cuántas solicitudes se envió (RF-92)."""
        filters = DocumentFilters(
            kind=query.kind.value if query.kind else None, archived=query.archived
        )
        return await self.documents.list(
            user_id, filters, page=query.page, limit=query.limit
        )

    async def get(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        document = await self.documents.get(user_id, document_id)
        if document is None:
            raise NotFoundError("Document")
        return document

    async def usage(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> Sequence[DocumentUsage]:
        """RF-92: en qué solicitudes se envió. 404 si el documento no es suyo."""
        await self.get(user_id, document_id)
        applications = await self.applications.list_using_document(user_id, document_id)
        return [
            DocumentUsage(
                application_id=application.id,
                position_title=application.position_title,
                company_name=application.company.name,
                used_as=DocumentKind.CV
                if application.cv_document_id == document_id
                else DocumentKind.COVER_LETTER,
                application_archived=application.archived_at is not None,
            )
            for application in applications
        ]

    async def rename(
        self, user_id: uuid.UUID, document_id: uuid.UUID, name: str
    ) -> Document:
        document = await self.get(user_id, document_id)
        document.name = sanitize_name(name)
        await self.documents.save(document)
        await self.session.commit()
        return document

    async def archive(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        """RF-93: fuera de la biblioteca, pero sigue asociado a sus solicitudes y
        ocupando almacenamiento. Idempotente: conserva la fecha del primero."""
        document = await self.get(user_id, document_id)
        if document.archived_at is None:
            document.archived_at = datetime.now(UTC)
            await self.documents.save(document)
            await self.session.commit()
        return document

    async def unarchive(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        document = await self.get(user_id, document_id)
        if document.archived_at is not None:
            document.archived_at = None
            await self.documents.save(document)
            await self.session.commit()
        return document

    async def delete(self, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
        """Borra la fila y, DESPUÉS del commit, el fichero (RNF-41, ficheros §5).
        Si falla el borrado del fichero, queda un huérfano que limpia el barrido;
        al revés quedaría una fila apuntando a nada."""
        document = await self.get(user_id, document_id)
        # RF-93: borrarlo perdería el dato de qué se envió a quién. La FK lo impide
        # igual; comprobarlo antes da un 409 con código en vez de un error de la BD.
        used = await self.applications.count_using_document(user_id, document_id)
        if used:
            raise DocumentInUseError(used)
        key = document.storage_key
        try:
            # La FK salta ya en el flush del repository, no solo en el commit.
            await self.documents.delete(document)
            await self.session.commit()
        except IntegrityError as exc:
            # Alguien lo asoció a una solicitud entre la comprobación y el borrado.
            await self.session.rollback()
            raise DocumentInUseError(1) from exc
        if key is None:
            return
        try:
            await self.storage.delete(key)
        except Exception:
            logger.exception(
                "No se pudo borrar el fichero del documento %s; lo limpiará el "
                "barrido de huérfanos",
                document_id,
            )

    async def open_file(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[Document, AsyncIterator[bytes]]:
        """El documento y su contenido, a trozos (ficheros §4). 404 si es de otro
        usuario (invariante 2); 409 `document_not_ready` si aún no tiene fichero
        (uno generado en `pending` o `failed`, F14)."""
        document = await self.get(user_id, document_id)
        if document.status != DocumentStatus.READY or document.storage_key is None:
            raise ConflictError("Document not ready", code="document_not_ready")
        try:
            chunks = await self.storage.open(document.storage_key)
        except StorageKeyNotFoundError:
            # No debería pasar: el fichero se escribe antes de confirmar la fila y
            # se borra después de borrarla. Si pasa, es un fallo que hay que ver.
            logger.error("Falta el fichero del documento %s", document.id)
            raise NotFoundError("Document") from None
        return document, chunks

    async def upload(
        self,
        user_id: uuid.UUID,
        *,
        kind: DocumentKind,
        name: str | None,
        body: AsyncIterable[bytes],
    ) -> Document:
        """Sube un PDF (ficheros §2, pasos 2 a 6). La sesión, la verificación del
        email y el rate limit (paso 1) los comprueba el endpoint."""
        # Paso 2: el tamaño real, cortando al pasarse. Content-Length lo declara el
        # cliente y puede mentir.
        data = await _read_at_most(body, self.config.document_max_bytes)

        # Paso 3: el tipo por el contenido, no por la extensión ni por el
        # Content-Type que diga el cliente.
        try:
            await count_pages(data, timeout=PDF_INSPECT_TIMEOUT_SECONDS)
        except InvalidPdfError as exc:
            raise InvalidFileTypeError() from exc

        # Paso 4: cuotas con la fila del usuario bloqueada (A30). Hasta el commit,
        # otra subida de la misma cuenta espera aquí y después ve esta.
        await self.users.lock(user_id)
        await self.limits.check(user_id, LimitKey.DOCUMENTS)
        await self.limits.check(user_id, LimitKey.STORAGE_BYTES, amount=len(data))

        # Paso 5: el fichero, de forma atómica, en una ruta que genera el servidor.
        document_id = uuid.uuid4()
        key = storage_key(user_id, document_id)
        size = await self.storage.put(key, _single_chunk(data))

        # Paso 6: la fila, y el commit. Si falla, el fichero queda huérfano.
        document = await self.documents.add(
            Document(
                id=document_id,
                user_id=user_id,
                kind=kind.value,
                origin=DocumentOrigin.UPLOADED.value,
                status=DocumentStatus.READY.value,
                name=sanitize_name(name),
                storage_key=key,
                size_bytes=size,
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )
        await self.session.commit()
        await self.session.refresh(document)
        return document


async def _read_at_most(body: AsyncIterable[bytes], max_bytes: int) -> bytes:
    """El cuerpo entero en memoria, o FileTooLargeAppError en cuanto pasa de
    `max_bytes`: se deja de leer ahí, sin esperar al final. En memoria porque se
    valida antes de escribirlo y el tope es pequeño (5 MB)."""
    buffer = bytearray()
    async for chunk in body:
        buffer += chunk
        if len(buffer) > max_bytes:
            raise FileTooLargeAppError(max_bytes)
    return bytes(buffer)


async def _single_chunk(data: bytes) -> AsyncIterator[bytes]:
    yield data
