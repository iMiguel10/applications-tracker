import hashlib
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import ConflictError, LimitReachedError, NotFoundError
from app.domain.cv import (
    CvDesign,
    CvSelection,
    CvSnapshot,
    SnapshotBullet,
    SnapshotContact,
    SnapshotEntry,
    SnapshotLanguage,
    SnapshotLink,
    SnapshotSkill,
    build_snapshot,
)
from app.domain.documents import (
    PENDING_GIVE_UP_AFTER,
    PENDING_REQUEUE_AFTER,
    PENDING_SWEEP_BATCH,
    DocumentErrorCode,
    DocumentKind,
    DocumentOrigin,
    DocumentStatus,
    sanitize_name,
    storage_key,
)
from app.domain.limits import LimitKey
from app.domain.profile import EntryKind
from app.infra.pdf import PdfRenderer
from app.infra.pdf.designs import CvDesignCatalog
from app.infra.queue import JobQueue, QueueUnavailableError
from app.infra.storage import FileStorage
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.profile_entry_repository import ProfileEntryRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.profile_skill_repository import ProfileSkillRepository
from app.repositories.user_repository import UserRepository
from app.schemas.cv import CvGenerateRequest
from app.services.cv_render_service import CvRenderService, resolve_design
from app.services.limit_service import LimitService

logger = logging.getLogger(__name__)

# El trabajo del `worker` que maqueta un documento pendiente (segundo plano §2).
GENERATE_DOCUMENT = "generate_document"
GENERATE_DOCUMENT_TIMEOUT_SECONDS = 60
# Generar es gratis e idempotente: se puede repetir sin riesgo (segundo plano §2).
GENERATE_DOCUMENT_MAX_ATTEMPTS = 3


class CvGenerationService:
    """Genera CVs desde el perfil (RF-103, flujo genérico de v2 §5).

    Al pedirlo se toma la foto fija del perfil (A27), se confirma la fila `pending`
    y, DESPUÉS del commit, se encola su maquetación (invariante 11). El `worker` la
    deja `ready` o `failed`; el frontend consulta la fila mientras tanto (A35).

    El almacén y el generador de PDF solo los necesita el `worker` (maquetar):
    la API no los recibe.
    """

    def __init__(
        self,
        session: AsyncSession,
        catalog: CvDesignCatalog | None = None,
        config: Settings = settings,
        *,
        storage: FileStorage | None = None,
        renderer: PdfRenderer | None = None,
    ) -> None:
        self.session = session
        self.catalog = catalog or CvDesignCatalog()
        self.storage = storage
        self.renderer = renderer
        self.documents = DocumentRepository(session)
        self.profiles = ProfileRepository(session)
        self.entries = ProfileEntryRepository(session)
        self.skills = ProfileSkillRepository(session)
        self.users = UserRepository(session)
        self.limits = LimitService(session, config)

    def designs(self) -> list[CvDesign]:
        return sorted(self.catalog.designs().values(), key=lambda design: design.key)

    async def request(
        self, user_id: uuid.UUID, data: CvGenerateRequest, job_queue: JobQueue
    ) -> Document:
        """Crea el CV `pending` y encola su maquetación. La sesión, el email
        verificado y el rate limit los comprueba el endpoint."""
        design = resolve_design(self.catalog, data.design, data.language)
        snapshot = await self.snapshot(
            user_id,
            CvSelection(
                sections=frozenset(data.sections),
                excluded_ids=frozenset(data.excluded_ids),
            ),
        )

        # Cuotas con la fila del usuario bloqueada (A30), como en una subida. El
        # tamaño del PDF no se sabe hasta maquetarlo: aquí solo se exige que quede
        # algo de almacenamiento, y el `worker` comprueba el tamaño real.
        await self.users.lock(user_id)
        await self.limits.check(user_id, LimitKey.DOCUMENTS)
        await self.limits.check(user_id, LimitKey.STORAGE_BYTES)

        document = await self.documents.add(
            Document(
                user_id=user_id,
                kind=DocumentKind.CV.value,
                origin=DocumentOrigin.GENERATED.value,
                status=DocumentStatus.PENDING.value,
                name=sanitize_name(data.name or f"CV {design.names[data.language]}"),
                template=design.key,
                language=data.language,
                content=snapshot.model_dump(mode="json"),
            )
        )
        await self.session.commit()
        await self.session.refresh(document)

        await self.enqueue(job_queue, document)
        return document

    async def enqueue(self, job_queue: JobQueue, document: Document) -> None:
        """Encola la maquetación de un documento ya confirmado (invariante 11). Si
        la cola no responde, no falla: la fila sigue `pending` y el barrido de
        pendientes la reencola (v2 §3)."""
        try:
            await job_queue.enqueue(
                GENERATE_DOCUMENT,
                timeout_seconds=GENERATE_DOCUMENT_TIMEOUT_SECONDS,
                max_attempts=GENERATE_DOCUMENT_MAX_ATTEMPTS,
                # SAQ guarda unos minutos los trabajos terminados con su clave y
                # no encola otro con la misma: con solo el id, reintentar un
                # fallido poco después se descartaría sin avisar. `updated_at`
                # cambia cada vez que el documento vuelve a `pending`.
                key=f"document:{document.id}:{document.updated_at.timestamp():.6f}",
                document_id=str(document.id),
                user_id=str(document.user_id),
            )
        except QueueUnavailableError:
            logger.warning(
                "Documento %s sin encolar; lo reencolará el barrido", document.id
            )

    async def retry(
        self, user_id: uuid.UUID, document_id: uuid.UUID, job_queue: JobQueue
    ) -> Document:
        """Vuelve a poner en cola un documento generado que falló, con la misma
        foto fija. 404 si no es suyo; 409 `document_not_failed` si no ha fallado."""
        # La misma cuota que al pedirlo: sin almacenamiento libre volvería a fallar.
        await self.users.lock(user_id)
        document = await self.documents.get(user_id, document_id)
        if document is None:
            raise NotFoundError("Document")
        if document.status != DocumentStatus.FAILED:
            raise ConflictError("Document has not failed", code="document_not_failed")
        await self.limits.check(user_id, LimitKey.STORAGE_BYTES)

        document.status = DocumentStatus.PENDING.value
        document.error_code = None
        await self.documents.save(document)
        await self.session.commit()
        await self.session.refresh(document)

        await self.enqueue(job_queue, document)
        return document

    async def render_pending(self, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
        """Maqueta un documento pendiente y lo deja `ready` o `failed` (trabajo
        `generate_document`). Idempotente: si ya no está `pending`, o si otra
        ejecución lo está maquetando, no hace nada.

        Escribe el fichero ANTES de confirmar la fila (invariante 15): si el commit
        falla, sobra un fichero que limpia el barrido de huérfanos."""
        assert self.storage is not None and self.renderer is not None, (
            "render_pending necesita el almacén y el generador de PDF"
        )
        # Bloqueado hasta el commit final (SKIP LOCKED en el repository).
        document = await self.documents.lock_pending(user_id, document_id)
        if document is None:
            return
        assert document.template is not None and document.language is not None

        try:
            snapshot = CvSnapshot.model_validate(document.content)
            pdf = await CvRenderService(self.renderer, self.catalog).render(
                snapshot, document.template, document.language
            )
        except Exception:
            # Maquetar es determinista: reintentar daría lo mismo. El usuario lo ve
            # fallido y puede reintentarlo él (por si cambió un diseño).
            logger.exception("No se pudo maquetar el documento %s", document.id)
            await self._fail(document, DocumentErrorCode.RENDER_FAILED)
            return

        # El tamaño real, con la fila del usuario bloqueada (A30): dos CVs que se
        # terminan a la vez no se pasan juntos del almacenamiento.
        await self.users.lock(user_id)
        try:
            await self.limits.check(user_id, LimitKey.STORAGE_BYTES, amount=len(pdf))
        except LimitReachedError:
            await self._fail(document, DocumentErrorCode.STORAGE_LIMIT_REACHED)
            return

        key = storage_key(user_id, document.id)
        size = await self.storage.put(key, _single_chunk(pdf))
        document.storage_key = key
        document.size_bytes = size
        document.sha256 = hashlib.sha256(pdf).hexdigest()
        document.status = DocumentStatus.READY.value
        await self.documents.save(document)
        await self.session.commit()

    async def sweep_pending(self, job_queue: JobQueue, now: datetime) -> None:
        """Barrido de pendientes (segundo plano §3): reencola los que llevan más de
        5 minutos en `pending` (su trabajo se perdió) y da por fallidos los que
        llevan más de una hora. Lee por páginas hasta agotarlos."""
        requeue_before = now - PENDING_REQUEUE_AFTER
        give_up_before = now - PENDING_GIVE_UP_AFTER
        after: tuple[datetime, uuid.UUID] | None = None
        while True:
            stale = await self.documents.stale_pending(
                requeue_before, PENDING_SWEEP_BATCH, after=after
            )
            if not stale:
                return
            after = (stale[-1].updated_at, stale[-1].id)
            requeue: list[Document] = []
            for document in stale:
                if document.updated_at < give_up_before:
                    logger.error(
                        "Documento %s pendiente más de una hora: se da por fallido",
                        document.id,
                    )
                    document.status = DocumentStatus.FAILED.value
                    document.error_code = DocumentErrorCode.RENDER_FAILED.value
                else:
                    requeue.append(document)
            await self.session.commit()
            for document in requeue:
                await self.enqueue(job_queue, document)
            if len(stale) < PENDING_SWEEP_BATCH:
                return

    async def _fail(self, document: Document, error: DocumentErrorCode) -> None:
        document.status = DocumentStatus.FAILED.value
        document.error_code = error.value
        await self.documents.save(document)
        await self.session.commit()

    async def snapshot(self, user_id: uuid.UUID, selection: CvSelection) -> CvSnapshot:
        """La foto fija del perfil con lo elegido (A27). Todo sale de las filas del
        usuario: un id ajeno en la selección no encuentra nada que quitar ni que
        poner."""
        profile = await self.profiles.get(user_id)
        entries = await self.entries.list(user_id)
        skills = await self.skills.skills(user_id)
        languages = await self.skills.languages(user_id)

        contact = SnapshotContact()
        if profile is not None:
            contact = SnapshotContact(
                full_name=profile.full_name,
                headline=profile.headline,
                email=profile.contact_email,
                phone=profile.phone,
                location=profile.location,
                links=[SnapshotLink.model_validate(link) for link in profile.links],
            )

        return build_snapshot(
            contact=contact,
            summary=profile.summary if profile is not None else None,
            entries=[
                SnapshotEntry(
                    id=entry.id,
                    title=entry.title,
                    organization=entry.organization,
                    location=entry.location,
                    start_date=entry.start_date,
                    end_date=entry.end_date,
                    is_current=entry.is_current,
                    description=entry.description,
                    bullets=[
                        SnapshotBullet(id=bullet.id, text=bullet.text)
                        for bullet in entry.bullets
                    ],
                )
                for entry in entries
            ],
            entry_kinds={entry.id: EntryKind(entry.kind) for entry in entries},
            skills=[
                SnapshotSkill(
                    id=skill.id,
                    name=skill.name,
                    category=skill.category,
                    level=skill.level,
                )
                for skill in skills
            ],
            languages=[
                SnapshotLanguage(id=item.id, language=item.language, level=item.level)
                for item in languages
            ],
            selection=selection,
        )


async def _single_chunk(data: bytes) -> AsyncIterator[bytes]:
    yield data
