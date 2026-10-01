"""Maquetar un CV pedido en el `worker`, reintentarlo y reencolar los atascados
(F14, segundo plano §2 y §3, invariante 15)."""

import io
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.domain.cv import CvSnapshot, SnapshotContact
from app.domain.limits import LimitKey
from app.infra.pdf.weasyprint_renderer import WeasyPrintRenderer
from app.infra.queue import InMemoryJobQueue
from app.infra.storage import LocalFileStorage
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.cv_generation_service import CvGenerationService
from app.services.limit_service import LimitService
from tests.conftest import create_test_user, test_engine
from tests.factories import make_document

SNAPSHOT = CvSnapshot(contact=SnapshotContact(full_name="Ana Pérez")).model_dump(
    mode="json"
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def storage(root: Path) -> LocalFileStorage:
    return LocalFileStorage(root)


def _files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and ".tmp" not in p.parts]


async def _pending(
    session: AsyncSession, user_id: uuid.UUID, **fields: Any
) -> Document:
    values: dict[str, Any] = {
        "origin": "generated",
        "status": "pending",
        "storage_key": None,
        "size_bytes": None,
        "sha256": None,
        "template": "classic",
        "language": "es",
        "content": SNAPSHOT,
    } | fields
    return await make_document(session, user_id, **values)


def _worker(session: AsyncSession, storage: LocalFileStorage) -> CvGenerationService:
    return CvGenerationService(session, storage=storage, renderer=WeasyPrintRenderer())


class BrokenRenderer:
    async def render(self, template_dir: Path, context: Mapping[str, Any]) -> bytes:
        raise RuntimeError("plantilla rota")


# --- Maquetar ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_pending_cv_is_rendered_written_and_left_ready(
    db_session: AsyncSession, user: CurrentUser, storage: LocalFileStorage, root: Path
):
    document = await _pending(db_session, user.id)

    await _worker(db_session, storage).render_pending(user.id, document.id)

    await db_session.refresh(document)
    assert (document.status, document.error_code) == ("ready", None)
    assert document.storage_key == f"users/{user.id}/documents/{document.id}.pdf"
    path = root / document.storage_key
    pdf = path.read_bytes()
    assert document.size_bytes == len(pdf)
    assert document.sha256 is not None and len(document.sha256) == 64
    assert "Ana Pérez" in PdfReader(io.BytesIO(pdf)).pages[0].extract_text()


@pytest.mark.asyncio
async def test_a_document_that_is_no_longer_pending_is_left_alone(
    db_session: AsyncSession, user: CurrentUser, storage: LocalFileStorage, root: Path
):
    # Idempotencia (segundo plano §2): encolar dos veces, o reencolar desde el
    # barrido uno que ya se maquetó, no lo vuelve a escribir.
    document = await make_document(db_session, user.id)

    await _worker(db_session, storage).render_pending(user.id, document.id)

    assert _files(root) == []


@pytest.mark.asyncio
async def test_the_job_of_another_user_finds_nothing(
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    storage: LocalFileStorage,
    root: Path,
):
    # El trabajo carga la fila por id Y user_id (v2 §5, paso 5).
    document = await _pending(db_session, user.id)

    await _worker(db_session, storage).render_pending(other_user.id, document.id)

    await db_session.refresh(document)
    assert document.status == "pending"
    assert _files(root) == []


@pytest.mark.asyncio
async def test_a_render_error_leaves_it_failed_without_a_file(
    db_session: AsyncSession, user: CurrentUser, storage: LocalFileStorage, root: Path
):
    document = await _pending(db_session, user.id)
    service = CvGenerationService(
        db_session, storage=storage, renderer=BrokenRenderer()
    )

    await service.render_pending(user.id, document.id)

    await db_session.refresh(document)
    assert (document.status, document.error_code) == ("failed", "render_failed")
    assert document.storage_key is None
    assert _files(root) == []


@pytest.mark.asyncio
async def test_a_design_that_no_longer_exists_fails_instead_of_crashing(
    db_session: AsyncSession, user: CurrentUser, storage: LocalFileStorage, root: Path
):
    document = await _pending(db_session, user.id, template="retirado")

    await _worker(db_session, storage).render_pending(user.id, document.id)

    await db_session.refresh(document)
    assert (document.status, document.error_code) == ("failed", "render_failed")


@pytest.mark.asyncio
async def test_the_real_size_is_checked_against_the_storage(
    db_session: AsyncSession, user: CurrentUser, storage: LocalFileStorage, root: Path
):
    # Al pedirlo solo se exige que quede algo; el tamaño real se sabe al maquetar.
    await make_document(db_session, user.id, size_bytes=1_000)
    await LimitService(db_session).set_override(user.id, LimitKey.STORAGE_BYTES, 1_100)
    document = await _pending(db_session, user.id)

    await _worker(db_session, storage).render_pending(user.id, document.id)

    await db_session.refresh(document)
    assert (document.status, document.error_code) == (
        "failed",
        "storage_limit_reached",
    )
    assert _files(root) == []


@pytest.mark.asyncio
async def test_the_same_document_rendered_twice_at_once_is_written_once(
    storage: LocalFileStorage,
    root: Path,
):
    # SAQ puede lanzar dos veces el mismo trabajo (segundo plano §2): mientras una
    # ejecución tiene el documento bloqueado, la otra no lo encuentra y no hace
    # nada. Con transacciones reales: con savepoints no hay dos sesiones.
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        document = await _pending(setup, owner.id)
        await setup.commit()
    first = AsyncSession(test_engine, expire_on_commit=False)
    second = AsyncSession(test_engine, expire_on_commit=False)
    try:
        locked = await DocumentRepository(first).lock_pending(owner.id, document.id)
        assert locked is not None

        await _worker(second, storage).render_pending(owner.id, document.id)

        assert _files(root) == []
        await first.rollback()
        await _worker(second, storage).render_pending(owner.id, document.id)
        assert len(_files(root)) == 1
    finally:
        await first.close()
        await second.close()
        async with AsyncSession(test_engine) as cleanup:
            await UserRepository(cleanup).delete(owner.id)
            await cleanup.commit()


# --- Reintentar -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_puts_a_failed_cv_back_in_the_queue_with_a_new_key(
    db_session: AsyncSession, user: CurrentUser
):
    document = await _pending(db_session, user.id)
    queue = InMemoryJobQueue()
    service = CvGenerationService(db_session)
    await service.enqueue(queue, document)
    document.status, document.error_code = "failed", "render_failed"
    await db_session.flush()

    retried = await service.retry(user.id, document.id, queue)

    assert (retried.status, retried.error_code) == ("pending", None)
    first, second = queue.jobs
    # SAQ descartaría un trabajo con la clave de uno que terminó hace poco.
    assert first.key != second.key
    assert second.kwargs == {"document_id": str(document.id), "user_id": str(user.id)}


@pytest.mark.asyncio
async def test_only_a_failed_document_can_be_retried(
    db_session: AsyncSession, user: CurrentUser
):
    document = await make_document(db_session, user.id)

    with pytest.raises(AppException) as error:
        await CvGenerationService(db_session).retry(
            user.id, document.id, InMemoryJobQueue()
        )

    assert error.value.code == "document_not_failed"


# --- Barrido de pendientes -----------------------------------------------------------


@pytest.mark.asyncio
async def test_the_sweep_requeues_stuck_ones_and_gives_up_after_an_hour(
    db_session: AsyncSession, user: CurrentUser
):
    now = datetime.now(UTC)
    fresh = await _pending(db_session, user.id, updated_at=now - timedelta(minutes=1))
    stuck = await _pending(db_session, user.id, updated_at=now - timedelta(minutes=10))
    lost = await _pending(db_session, user.id, updated_at=now - timedelta(hours=2))
    ready = await make_document(
        db_session, user.id, updated_at=now - timedelta(hours=2)
    )
    queue = InMemoryJobQueue()

    await CvGenerationService(db_session).sweep_pending(queue, now)

    assert [job.kwargs["document_id"] for job in queue.jobs] == [str(stuck.id)]
    for document in (fresh, stuck, lost, ready):
        await db_session.refresh(document)
    assert (fresh.status, stuck.status, ready.status) == ("pending", "pending", "ready")
    assert (lost.status, lost.error_code) == ("failed", "render_failed")


@pytest.mark.asyncio
async def test_the_sweep_reads_every_page(
    db_session: AsyncSession, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
):
    # Una pasada lee por páginas hasta agotarlas: si leyera una sola, los mismos
    # atascados la ocuparían en cada pasada.
    monkeypatch.setattr("app.services.cv_generation_service.PENDING_SWEEP_BATCH", 2)
    now = datetime.now(UTC)
    stuck = [
        await _pending(
            db_session, user.id, updated_at=now - timedelta(minutes=10 + minute)
        )
        for minute in range(5)
    ]
    queue = InMemoryJobQueue()

    await CvGenerationService(db_session).sweep_pending(queue, now)

    assert sorted(str(job.kwargs["document_id"]) for job in queue.jobs) == sorted(
        str(document.id) for document in stuck
    )
