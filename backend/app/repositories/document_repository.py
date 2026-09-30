import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.document import Document


@dataclass(frozen=True)
class DocumentFilters:
    """Filtros del listado de la biblioteca. Objeto plano: el repository no depende
    de HTTP."""

    kind: str | None = None
    # False: la biblioteca (sin archivados). True: solo los archivados (RF-93).
    archived: bool = False


class DocumentRepository:
    """Acceso a `documents`. Todo método recibe `user_id` y filtra por él
    (invariante 1). Nunca hace commit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.flush()
        return document

    async def get(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        return await self.session.scalar(
            select(Document).where(
                Document.id == document_id, Document.user_id == user_id
            )
        )

    async def save(self, document: Document) -> Document:
        """Envía a la BD los cambios de un documento ya cargado (UPDATE)."""
        await self.session.flush()
        return document

    async def delete(self, document: Document) -> None:
        await self.session.delete(document)
        await self.session.flush()

    async def list(
        self,
        user_id: uuid.UUID,
        filters: DocumentFilters,
        *,
        page: int,
        limit: int,
    ) -> tuple[list[tuple[Document, int]], int]:
        """Los más recientes primero, cada uno con en cuántas solicitudes se envió
        (RF-92): una subconsulta por fila de la página, sobre los índices parciales
        de las dos FK."""
        used_in = (
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == Document.user_id,
                or_(
                    Application.cv_document_id == Document.id,
                    Application.cover_letter_document_id == Document.id,
                ),
            )
            .correlate(Document)
            .scalar_subquery()
        )
        query = select(Document).where(Document.user_id == user_id)
        if filters.kind:
            query = query.where(Document.kind == filters.kind)
        query = query.where(
            Document.archived_at.is_not(None)
            if filters.archived
            else Document.archived_at.is_(None)
        )

        total = await self.session.scalar(
            select(func.count()).select_from(
                query.with_only_columns(Document.id).subquery()
            )
        )
        result = await self.session.execute(
            query.add_columns(used_in)
            .order_by(Document.created_at.desc(), Document.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return [(document, count) for document, count in result.tuples()], total or 0

    async def count(self, user_id: uuid.UUID) -> int:
        """Para el límite de documentos: todos, archivados incluidos."""
        total = await self.session.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.user_id == user_id)
        )
        return total or 0

    async def total_size(self, user_id: uuid.UUID) -> int:
        """Almacenamiento usado: la suma de los bytes escritos de verdad. Los
        archivados cuentan (su fichero sigue en disco) y los `pending` aún no
        tienen tamaño."""
        total = await self.session.scalar(
            select(func.coalesce(func.sum(Document.size_bytes), 0)).where(
                Document.user_id == user_id
            )
        )
        return int(total or 0)

    async def existing_storage_keys(self, keys: Sequence[str]) -> set[str]:
        """De estas claves del almacén, las que tienen fila (ficheros §5).

        Sin `user_id` a propósito: es el barrido de huérfanos, que recorre el
        almacén de todas las cuentas; solo devuelve claves, nunca datos."""
        if not keys:
            return set()
        result = await self.session.scalars(
            select(Document.storage_key).where(Document.storage_key.in_(keys))
        )
        return {key for key in result.all() if key is not None}
