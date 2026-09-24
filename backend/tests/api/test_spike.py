"""DESECHABLE (F9): pruebas del esqueleto vertical. Se borran con él."""

import uuid
from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_file_storage, get_job_queue
from app.infra.email.recording import RecordingEmailSender
from app.infra.queue import InMemoryJobQueue
from app.infra.storage import LocalFileStorage
from app.main import app
from app.repositories.identity_repository import IdentityRepository
from app.schemas.user import CurrentUser
from app.services.spike_service import SPIKE_PDF_JOB, SpikePdfService, spike_pdf_key


class FakeIdentities(IdentityRepository):
    """Sin core de SuperTokens: cada usuario tiene un email inventado."""

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return f"{supertokens_user_id}@example.com"


class FakeRenderer:
    async def render(self, template_dir: Path, context: Mapping[str, Any]) -> bytes:
        return b"%PDF-falso"


async def chunks(content: bytes) -> AsyncIterator[bytes]:
    yield content


@pytest.fixture
def queue() -> InMemoryJobQueue:
    queue = InMemoryJobQueue()
    app.dependency_overrides[get_job_queue] = lambda: queue
    return queue


@pytest.fixture
def storage(tmp_path: Path, queue: InMemoryJobQueue) -> LocalFileStorage:
    storage = LocalFileStorage(tmp_path)
    app.dependency_overrides[get_file_storage] = lambda: storage
    return storage


@pytest.mark.asyncio
async def test_request_pdf_enqueues_and_returns_202(
    client: AsyncClient,
    user: CurrentUser,
    queue: InMemoryJobQueue,
    storage: LocalFileStorage,
) -> None:
    response = await client.post("/api/v1/spike/pdf")

    assert response.status_code == 202
    file_id = response.json()["file_id"]
    [job] = queue.jobs
    assert job.job == SPIKE_PDF_JOB
    assert job.kwargs == {"user_id": str(user.id), "file_id": file_id}
    assert job.max_attempts == 1


@pytest.mark.asyncio
async def test_download_serves_the_pdf_with_safe_headers(
    client: AsyncClient, user: CurrentUser, storage: LocalFileStorage
) -> None:
    file_id = uuid.uuid4()
    await storage.put(spike_pdf_key(user.id, file_id), chunks(b"%PDF-contenido"))

    response = await client.get(f"/api/v1/spike/pdf/{file_id}")

    assert response.status_code == 200
    assert response.content == b"%PDF-contenido"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"
    # D8: nombre con tilde → versión ASCII y filename* en UTF-8.
    assert response.headers["content-disposition"] == (
        'inline; filename="prueba-curriculum.pdf"; '
        "filename*=UTF-8''prueba-curr%C3%ADculum.pdf"
    )


@pytest.mark.asyncio
async def test_download_of_another_users_pdf_is_404(
    client: AsyncClient,
    other_user: CurrentUser,
    storage: LocalFileStorage,
) -> None:
    """El PDF existe, pero la ruta se construye con el user_id de quien pide."""
    file_id = uuid.uuid4()
    await storage.put(spike_pdf_key(other_user.id, file_id), chunks(b"%PDF-ajeno"))

    response = await client.get(f"/api/v1/spike/pdf/{file_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_worker_side_generates_stores_and_emails(
    db_session: AsyncSession, user: CurrentUser, storage: LocalFileStorage
) -> None:
    sender = RecordingEmailSender()
    file_id = uuid.uuid4()
    service = SpikePdfService(
        db_session,
        pdf_renderer=FakeRenderer(),
        storage=storage,
        email_sender=sender,
        identities=FakeIdentities(),
        api_url="http://localhost:8000/",
    )

    await service.generate_and_send(user.id, file_id)

    stored = await storage.open(spike_pdf_key(user.id, file_id))
    assert b"".join([chunk async for chunk in stored]) == b"%PDF-falso"
    [email] = sender.sent
    assert email.to == f"{user.supertokens_user_id}@example.com"
    assert f"http://localhost:8000/api/v1/spike/pdf/{file_id}" in email.text
