import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def list(
        self,
        user_id: uuid.UUID,
        filters: DocumentFilters,
        *,
        page: int,
        limit: int,
    ) -> tuple[list[Document], int]:
        """Los más recientes primero."""
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
        result = await self.session.scalars(
            query.order_by(Document.created_at.desc(), Document.id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return list(result.all()), total or 0

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
