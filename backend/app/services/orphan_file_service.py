import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents import ORPHAN_GRACE, ORPHAN_SWEEP_BATCH
from app.infra.storage import FileStorage, StoredFile
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrphanSweepResult:
    files: int
    temporaries: int


class OrphanFileService:
    """Barrido de ficheros huérfanos (ficheros §5).

    Postgres manda (invariante 9 de v2) y el orden de escritura hace que solo
    puedan **sobrar** ficheros: el de una subida cuya fila no llegó a confirmarse,
    el de un documento cuyo borrado de fichero falló, los de una cuenta borrada si
    falló `delete_prefix`, o un temporal de un proceso que murió escribiendo. Este
    barrido los borra; nunca toca uno más reciente que `ORPHAN_GRACE`, que podría
    ser una subida en curso.
    """

    def __init__(self, session: AsyncSession, storage: FileStorage) -> None:
        self.session = session
        self.storage = storage
        self.documents = DocumentRepository(session)

    async def sweep(self, now: datetime) -> OrphanSweepResult:
        """`now` como parámetro: el reloj real solo se lee en el trabajo."""
        cutoff = now - ORPHAN_GRACE
        deleted = 0
        batch: list[StoredFile] = []
        async for stored in self.storage.iter_files():
            if stored.modified_at >= cutoff:
                continue
            batch.append(stored)
            if len(batch) >= ORPHAN_SWEEP_BATCH:
                deleted += await self._delete_orphans(batch)
                batch = []
        deleted += await self._delete_orphans(batch)
        temporaries = await self.storage.delete_temporaries(cutoff)
        if deleted or temporaries:
            logger.info(
                "Barrido de huérfanos: %d ficheros y %d temporales borrados",
                deleted,
                temporaries,
            )
        return OrphanSweepResult(files=deleted, temporaries=temporaries)

    async def _delete_orphans(self, batch: list[StoredFile]) -> int:
        if not batch:
            return 0
        existing = await self.documents.existing_storage_keys(
            [stored.key for stored in batch]
        )
        deleted = 0
        for stored in batch:
            if stored.key in existing:
                continue
            await self.storage.delete(stored.key)
            deleted += 1
        return deleted
