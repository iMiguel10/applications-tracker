import hashlib
import uuid
from collections.abc import AsyncIterable, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import FileTooLargeAppError, InvalidFileTypeError
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
from app.infra.storage import FileStorage
from app.models.document import Document
from app.repositories.document_repository import DocumentFilters, DocumentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.document import DocumentListQuery
from app.services.limit_service import LimitService


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
        self.users = UserRepository(session)
        self.limits = LimitService(session, config)

    async def list(
        self, user_id: uuid.UUID, query: DocumentListQuery
    ) -> tuple[list[Document], int]:
        filters = DocumentFilters(
            kind=query.kind.value if query.kind else None, archived=query.archived
        )
        return await self.documents.list(
            user_id, filters, page=query.page, limit=query.limit
        )

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
