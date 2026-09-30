"""Carreras de la biblioteca de documentos con transacciones reales (ficheros §2
y §8, D3 y D5; A30).

Añadidas por el qa-verifier al cerrar F13. Como en D3, cada sesión es una
transacción de verdad contra `db-test` y el usuario se borra al terminar.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, DocumentInUseError, NotFoundError
from app.domain.documents import DocumentKind
from app.domain.limits import LimitKey
from app.infra.storage import LocalFileStorage
from app.models.application import Application
from app.models.document import Document
from app.repositories.user_repository import UserRepository
from app.schemas.application import ApplicationUpdate
from app.schemas.user import CurrentUser
from app.services.application_service import ApplicationService
from app.services.document_service import DocumentService
from app.services.limit_service import LimitService
from tests.conftest import create_test_user, test_engine
from tests.factories import make_application, make_document
from tests.pdf_helpers import make_pdf

# Tiempo para que la sentencia bloqueada llegue a esperar el bloqueo de la otra.
LOCK_WAIT_SECONDS = 0.5


async def _chunks(content: bytes) -> AsyncIterator[bytes]:
    yield content


async def _delete_user(user_id: uuid.UUID) -> None:
    async with AsyncSession(test_engine) as cleanup:
        await UserRepository(cleanup).delete(user_id)
        await cleanup.commit()


async def _owner_with_application_and_cv() -> tuple[CurrentUser, uuid.UUID, uuid.UUID]:
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        application = await make_application(setup, owner.id)
        cv = await make_document(setup, owner.id, kind="cv")
        await setup.commit()
        return owner, application.id, cv.id


@pytest.mark.asyncio
async def test_two_simultaneous_uploads_cannot_exceed_the_document_limit_together(
    tmp_path: Path,
):
    # D3 para el límite de documentos (el test existente cubre el almacenamiento):
    # con un hueco, de dos subidas a la vez solo entra una.
    content = make_pdf()
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        await LimitService(setup).set_override(owner.id, LimitKey.DOCUMENTS, 1)
        await setup.commit()
    storage = LocalFileStorage(tmp_path)
    session_a = AsyncSession(test_engine, expire_on_commit=False)
    session_b = AsyncSession(test_engine, expire_on_commit=False)

    async def upload(session: AsyncSession) -> str:
        try:
            await DocumentService(session, storage).upload(
                owner.id, kind=DocumentKind.CV, name="cv.pdf", body=_chunks(content)
            )
        except AppException as exc:
            await session.rollback()
            return exc.code
        return "ok"

    try:
        results = await asyncio.gather(upload(session_a), upload(session_b))

        assert sorted(results) == ["documents_limit_reached", "ok"]
        stored = [p for p in tmp_path.rglob("*.pdf") if ".tmp" not in p.parts]
        assert len(stored) == 1
    finally:
        await session_a.close()
        await session_b.close()
        await _delete_user(owner.id)


# Encontrado por el qa-verifier en F13: `DocumentRepository.delete` hace flush, así
# que la FK salta ahí, y el `try/except IntegrityError` solo envolvía el commit.
@pytest.mark.asyncio
async def test_deleting_a_document_while_it_is_being_assigned_is_a_409_not_a_500(
    tmp_path: Path,
):
    # D5 en carrera. Otra petición asigna el CV a una solicitud y aún no ha
    # confirmado: el DELETE ve 0 usos, espera al bloqueo que la FK deja en la fila
    # del documento y, cuando la otra confirma, la FK lo rechaza. Debe ser el mismo
    # 409 `document_in_use` que sin carrera, no un IntegrityError (500).
    owner, application_id, cv_id = await _owner_with_application_and_cv()
    assigning = AsyncSession(test_engine, expire_on_commit=False)
    deleting = AsyncSession(test_engine, expire_on_commit=False)
    try:
        await assigning.execute(
            update(Application)
            .where(Application.id == application_id, Application.user_id == owner.id)
            .values(cv_document_id=cv_id)
        )
        task = asyncio.create_task(
            DocumentService(deleting, LocalFileStorage(tmp_path)).delete(
                owner.id, cv_id
            )
        )
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not task.done(), "el DELETE debería estar esperando el bloqueo"
        await assigning.commit()

        with pytest.raises(DocumentInUseError):
            await task
    finally:
        await assigning.close()
        await deleting.rollback()
        await deleting.close()
        await _delete_user(owner.id)


# Encontrado por el qa-verifier en F13: `ApplicationService` no traducía el
# IntegrityError de la FK a documentos (`create` y `update`).
@pytest.mark.asyncio
async def test_assigning_a_document_that_is_being_deleted_is_not_a_500():
    # La carrera al revés: el documento se está borrando (sin confirmar) cuando
    # otra petición lo asigna. `_ensure_documents` aún lo ve; el UPDATE espera al
    # bloqueo y, al confirmarse el borrado, la FK lo rechaza. Debe ser el mismo 404
    # que un documento que no existe, no un IntegrityError (500).
    owner, application_id, cv_id = await _owner_with_application_and_cv()
    deleting = AsyncSession(test_engine, expire_on_commit=False)
    assigning = AsyncSession(test_engine, expire_on_commit=False)
    try:
        await deleting.execute(
            delete(Document).where(Document.id == cv_id, Document.user_id == owner.id)
        )
        task = asyncio.create_task(
            ApplicationService(assigning).update(
                owner.id, application_id, ApplicationUpdate(cv_document_id=cv_id)
            )
        )
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not task.done(), "el UPDATE debería estar esperando el bloqueo"
        await deleting.commit()

        with pytest.raises(NotFoundError):
            await task
    finally:
        await deleting.close()
        await assigning.rollback()
        await assigning.close()
        await _delete_user(owner.id)
