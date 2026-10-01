"""Carreras y entradas hostiles al generar CVs (F14, segundo plano §2-§3, ficheros
§7, A30, invariante 15).

Añadidas por el qa-verifier al cerrar F14. Las carreras usan transacciones reales
contra `db-test` (con savepoints no hay dos sesiones) y borran al usuario al
terminar, como `test_document_races.py`.
"""

import asyncio
import io
import uuid
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.domain.cv import CvSnapshot, SnapshotContact, SnapshotLink
from app.domain.limits import LimitKey
from app.infra.pdf.weasyprint_renderer import WeasyPrintRenderer
from app.infra.queue import InMemoryJobQueue
from app.infra.storage import LocalFileStorage
from app.models.document import Document
from app.repositories.user_repository import UserRepository
from app.schemas.cv import CvGenerateRequest
from app.schemas.user import CurrentUser
from app.services.cv_generation_service import CvGenerationService
from app.services.document_service import DocumentService
from app.services.limit_service import LimitService
from tests.conftest import create_test_user, test_engine
from tests.factories import make_document
from tests.infra.test_pdf import CountingServer

# Tiempo para que la sentencia bloqueada llegue a esperar el bloqueo de la otra.
LOCK_WAIT_SECONDS = 0.5

SNAPSHOT = CvSnapshot(contact=SnapshotContact(full_name="Ana Pérez")).model_dump(
    mode="json"
)


def _pending_fields(**fields: Any) -> dict[str, Any]:
    return {
        "origin": "generated",
        "status": "pending",
        "storage_key": None,
        "size_bytes": None,
        "sha256": None,
        "template": "classic",
        "language": "es",
        "content": SNAPSHOT,
    } | fields


def _files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and ".tmp" not in p.parts]


async def _delete_user(user_id: uuid.UUID) -> None:
    async with AsyncSession(test_engine) as cleanup:
        await UserRepository(cleanup).delete(user_id)
        await cleanup.commit()


async def _owner_with(**document_fields: Any) -> tuple[CurrentUser, uuid.UUID]:
    """Un usuario confirmado de verdad con un documento generado."""
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        document = await make_document(
            setup, owner.id, **_pending_fields(**document_fields)
        )
        await setup.commit()
        return owner, document.id


class GatedRenderer:
    """Un generador de PDF que se para a mitad de maquetar hasta que se le deja
    seguir: así la otra transacción llega mientras el `worker` tiene el documento
    bloqueado."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self._real = WeasyPrintRenderer()

    async def render(self, template_dir: Path, context: Mapping[str, Any]) -> bytes:
        self.entered.set()
        await self.release.wait()
        return await self._real.render(template_dir, context)


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(tmp_path)


# --- Borrar mientras el worker maqueta ------------------------------------------------


@pytest.mark.asyncio
async def test_deleting_the_account_while_its_cv_is_being_rendered_fails_neither(
    storage: LocalFileStorage, tmp_path: Path
):
    # El usuario borra su cuenta (DELETE /me: `users` y, en cascada, el documento)
    # mientras el `worker` maqueta su CV. Ninguna de las dos debe fallar: un
    # DELETE /me que falla es un 500 para el usuario. Era un deadlock cuando el
    # worker bloqueaba el documento antes de maquetar y el usuario después (el
    # orden contrario al del borrado); ahora maqueta sin bloquear nada, así que el
    # borrado no espera, y al terminar el worker ya no encuentra el documento.
    owner, document_id = await _owner_with()
    renderer = GatedRenderer()
    rendering = AsyncSession(test_engine, expire_on_commit=False)
    deleting = AsyncSession(test_engine, expire_on_commit=False)

    async def delete_account() -> None:
        await UserRepository(deleting).delete(owner.id)
        await deleting.commit()

    try:
        render_task = asyncio.create_task(
            CvGenerationService(
                rendering, storage=storage, renderer=renderer
            ).render_pending(owner.id, document_id)
        )
        await asyncio.wait_for(renderer.entered.wait(), timeout=5)
        delete_task = asyncio.create_task(delete_account())
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        renderer.release.set()

        render_result, delete_result = await asyncio.gather(
            render_task, delete_task, return_exceptions=True
        )

        assert delete_result is None, f"DELETE /me falló: {delete_result!r}"
        assert render_result is None, f"el trabajo falló: {render_result!r}"
        # El worker no escribe el PDF de una cuenta que ya no existe.
        assert _files(tmp_path) == []
    finally:
        renderer.release.set()
        await rendering.rollback()
        await rendering.close()
        await deleting.rollback()
        await deleting.close()
        await _delete_user(owner.id)


@pytest.mark.asyncio
async def test_deleting_a_cv_while_it_is_being_rendered_leaves_no_row_behind(
    storage: LocalFileStorage, tmp_path: Path
):
    # El usuario borra un CV `pending` mientras el `worker` lo maqueta. El borrado
    # no espera (el worker maqueta sin bloquear nada) y, al terminar, el worker ya
    # no lo encuentra `pending`: ninguna fila sin fichero (invariante 15) y, aquí,
    # tampoco un fichero sin fila.
    owner, document_id = await _owner_with()
    renderer = GatedRenderer()
    rendering = AsyncSession(test_engine, expire_on_commit=False)
    deleting = AsyncSession(test_engine, expire_on_commit=False)
    try:
        render_task = asyncio.create_task(
            CvGenerationService(
                rendering, storage=storage, renderer=renderer
            ).render_pending(owner.id, document_id)
        )
        await asyncio.wait_for(renderer.entered.wait(), timeout=5)
        delete_task = asyncio.create_task(
            DocumentService(deleting, storage).delete(owner.id, document_id)
        )
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        renderer.release.set()

        render_result, delete_result = await asyncio.gather(
            render_task, delete_task, return_exceptions=True
        )

        assert render_result is None, f"el trabajo falló: {render_result!r}"
        assert delete_result is None, f"el borrado falló: {delete_result!r}"
        async with AsyncSession(test_engine) as check:
            assert await check.get(Document, document_id) is None
        # El worker revalida que sigue `pending` antes de escribir: un CV borrado
        # mientras se maquetaba no deja ni fila ni fichero.
        assert _files(tmp_path) == []
    finally:
        renderer.release.set()
        await rendering.close()
        await deleting.close()
        await _delete_user(owner.id)


# --- Cuotas y reintentos simultáneos ---------------------------------------------------


@pytest.mark.asyncio
async def test_two_simultaneous_generates_cannot_exceed_the_document_limit_together():
    # A30: con un hueco, de dos peticiones a la vez solo entra una (sin la fila del
    # usuario bloqueada, las dos contarían 0 y entrarían).
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        await LimitService(setup).set_override(owner.id, LimitKey.DOCUMENTS, 1)
        await setup.commit()
    queue = InMemoryJobQueue()
    session_a = AsyncSession(test_engine, expire_on_commit=False)
    session_b = AsyncSession(test_engine, expire_on_commit=False)

    async def generate(session: AsyncSession) -> str:
        try:
            await CvGenerationService(session).request(
                owner.id, CvGenerateRequest(design="classic", language="es"), queue
            )
        except AppException as exc:
            await session.rollback()
            return exc.code
        return "ok"

    try:
        results = await asyncio.gather(generate(session_a), generate(session_b))

        assert sorted(results) == ["documents_limit_reached", "ok"]
        assert len(queue.jobs) == 1
        async with AsyncSession(test_engine) as check:
            rows = await check.scalars(
                select(Document.id).where(Document.user_id == owner.id)
            )
            assert len(rows.all()) == 1
    finally:
        await session_a.close()
        await session_b.close()
        await _delete_user(owner.id)


@pytest.mark.asyncio
async def test_two_simultaneous_retries_of_a_failed_cv_enqueue_it_once():
    # Doble clic en "Reintentar" o dos pestañas: el segundo ve el documento ya
    # `pending` y responde 409, y en la cola hay un solo trabajo.
    owner, document_id = await _owner_with(status="failed", error_code="render_failed")
    queue = InMemoryJobQueue()
    session_a = AsyncSession(test_engine, expire_on_commit=False)
    session_b = AsyncSession(test_engine, expire_on_commit=False)

    async def retry(session: AsyncSession) -> str:
        try:
            await CvGenerationService(session).retry(owner.id, document_id, queue)
        except AppException as exc:
            await session.rollback()
            return exc.code
        return "ok"

    try:
        results = await asyncio.gather(retry(session_a), retry(session_b))

        assert sorted(results) == ["document_not_failed", "ok"]
        assert len(queue.jobs) == 1
    finally:
        await session_a.close()
        await session_b.close()
        await _delete_user(owner.id)


@pytest.mark.asyncio
async def test_retrying_someone_elses_failed_cv_is_a_404_and_changes_nothing(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    document = await make_document(
        db_session,
        other_user.id,
        **_pending_fields(status="failed", error_code="render_failed"),
    )
    queue = InMemoryJobQueue()

    with pytest.raises(AppException) as error:
        await CvGenerationService(db_session).retry(user.id, document.id, queue)

    assert error.value.status_code == 404
    await db_session.refresh(document)
    assert (document.status, document.error_code) == ("failed", "render_failed")
    assert queue.jobs == []


# --- El barrido con varias cuentas ----------------------------------------------------


@pytest.mark.asyncio
async def test_the_sweep_requeues_each_stuck_cv_with_its_own_owner(
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    storage: LocalFileStorage,
    tmp_path: Path,
):
    # El barrido recorre todas las cuentas; cada trabajo debe llevar el `user_id`
    # del dueño de la fila, o el worker (que carga por id Y user_id) no la
    # encontraría y se quedaría `pending` hasta darse por perdida.
    now = datetime.now(UTC)
    stuck = {
        user.id: await make_document(
            db_session,
            user.id,
            **_pending_fields(updated_at=now - timedelta(minutes=10)),
        ),
        other_user.id: await make_document(
            db_session,
            other_user.id,
            **_pending_fields(updated_at=now - timedelta(minutes=20)),
        ),
    }
    queue = InMemoryJobQueue()

    await CvGenerationService(db_session).sweep_pending(queue, now)

    assert sorted(
        (j.kwargs["user_id"], j.kwargs["document_id"]) for j in queue.jobs
    ) == (sorted((str(owner), str(doc.id)) for owner, doc in stuck.items()))
    worker = CvGenerationService(
        db_session, storage=storage, renderer=WeasyPrintRenderer()
    )
    for job in queue.jobs:
        await worker.render_pending(
            uuid.UUID(str(job.kwargs["user_id"])),
            uuid.UUID(str(job.kwargs["document_id"])),
        )
    for document in stuck.values():
        await db_session.refresh(document)
        assert document.status == "ready"
        assert document.storage_key is not None
        assert document.storage_key.startswith(f"users/{document.user_id}/")


# --- Contenido hostil --------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        {"contact": "no es un objeto"},
        {"contact": {"full_name": "Ana"}, "entry_sections": [{"section": "photo"}]},
        {"contact": {}, "skills": [{"id": "no-es-un-id", "name": "SQL"}]},
        [],
    ],
)
async def test_a_tampered_snapshot_fails_the_cv_instead_of_crashing_the_job(
    db_session: AsyncSession,
    user: CurrentUser,
    storage: LocalFileStorage,
    tmp_path: Path,
    content: Any,
):
    # La foto fija se valida al maquetar: una fila con `content` que no es una foto
    # válida (otra versión, una edición a mano) queda `failed` sin fichero, no
    # revienta el trabajo (que SAQ reintentaría).
    document = await make_document(
        db_session, user.id, **_pending_fields(content=content)
    )

    await CvGenerationService(
        db_session, storage=storage, renderer=WeasyPrintRenderer()
    ).render_pending(user.id, document.id)

    await db_session.refresh(document)
    assert (document.status, document.error_code) == ("failed", "render_failed")
    assert _files(tmp_path) == []


@pytest.fixture
def counting_server() -> Iterator[CountingServer]:
    with CountingServer() as server:
        yield server


@pytest.mark.asyncio
@pytest.mark.parametrize("design", ["classic", "modern", "compact", "graphic"])
async def test_html_in_the_profile_is_printed_as_text_and_fetches_nothing(
    db_session: AsyncSession,
    user: CurrentUser,
    storage: LocalFileStorage,
    tmp_path: Path,
    counting_server: CountingServer,
    design: str,
):
    # D9 de punta a punta con los diseños reales: lo que escribe el usuario (o, en
    # F15, la IA) no es HTML. Ni una imagen, ni una hoja de estilos, ni un
    # `@import` producen una petición; el texto sale tal cual en el PDF; y un
    # enlace del perfil es un enlace del PDF, que WeasyPrint no descarga.
    url = counting_server.url
    hostile = (
        f'<img src="{url}/img"><link rel="stylesheet" href="{url}/css">'
        f"<style>@import url({url}/import);</style>"
    )
    snapshot = CvSnapshot(
        contact=SnapshotContact(
            full_name=f"Ana {hostile}",
            headline=hostile,
            links=[SnapshotLink(label="Web", url=f"{url}/link")],
        ),
        summary=hostile,
    ).model_dump(mode="json")
    document = await make_document(
        db_session, user.id, **_pending_fields(template=design, content=snapshot)
    )

    await CvGenerationService(
        db_session, storage=storage, renderer=WeasyPrintRenderer()
    ).render_pending(user.id, document.id)

    await db_session.refresh(document)
    assert document.status == "ready"
    assert counting_server.requests == []
    assert document.storage_key is not None
    pdf = (tmp_path / document.storage_key).read_bytes()
    text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "<img" in text
