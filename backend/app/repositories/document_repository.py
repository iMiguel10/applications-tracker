import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.flush()
        return document

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
