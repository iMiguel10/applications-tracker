"""Generar un CV desde el perfil: la petición (F14, RF-103, A27, A35, v2 §5).

La maquetación en el `worker` se prueba en tests/services/test_cv_generation.py.
"""

import uuid
from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_job_queue
from app.core.config import settings
from app.domain.limits import LimitKey
from app.domain.profile import EntryKind
from app.infra.queue import InMemoryJobQueue, JobArg, QueueUnavailableError
from app.infra.rate_limit import DisabledRateLimiter, LimitsRateLimiter
from app.main import app
from app.models.document import Document
from app.schemas.user import CurrentUser
from app.services.limit_service import LimitService
from tests.auth_helpers import PASSWORD, form
from tests.factories import make_document, make_profile_entry

URL = "/api/v1/documents/generate"
DESIGNS_URL = "/api/v1/documents/cv-designs"


@pytest.fixture
def queue() -> Iterator[InMemoryJobQueue]:
    job_queue = InMemoryJobQueue()
    app.dependency_overrides[get_job_queue] = lambda: job_queue
    yield job_queue
    app.dependency_overrides.pop(get_job_queue, None)


async def _document(db_session: AsyncSession, document_id: str) -> Document:
    document = await db_session.get(Document, uuid.UUID(document_id))
    assert document is not None
    await db_session.refresh(document)
    return document


@pytest.mark.asyncio
async def test_the_designs_are_listed_with_the_graphic_one_marked(client: AsyncClient):
    response = await client.get(DESIGNS_URL)

    assert response.status_code == 200
    designs = {design["key"]: design for design in response.json()}
    assert sorted(designs) == ["classic", "compact", "graphic", "modern"]
    assert [key for key, d in designs.items() if not d["ats_friendly"]] == ["graphic"]
    assert designs["modern"]["names"] == {"es": "Moderno", "en": "Modern"}


@pytest.mark.asyncio
async def test_generate_creates_a_pending_cv_with_a_snapshot_and_enqueues_it(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    await client.put("/api/v1/profile", json={"full_name": "Ana Pérez"})
    job = await make_profile_entry(
        db_session, user.id, title="Backend", bullets=["SQL"]
    )

    response = await client.post(URL, json={"design": "modern", "language": "es"})

    assert response.status_code == 202
    body = response.json()
    assert body["origin"] == "generated"
    assert body["status"] == "pending"
    assert (body["template"], body["language"], body["error_code"]) == (
        "modern",
        "es",
        None,
    )
    assert body["name"] == "CV Moderno"
    assert body["size_bytes"] is None

    document = await _document(db_session, body["id"])
    assert document.storage_key is None
    assert document.content is not None
    assert document.content["contact"]["full_name"] == "Ana Pérez"
    [section] = document.content["entry_sections"]
    assert section["entries"][0]["id"] == str(job.id)
    assert section["entries"][0]["bullets"][0]["text"] == "SQL"

    # Solo ids: el worker carga lo demás de la BD (segundo plano §2).
    [enqueued] = queue.jobs
    assert enqueued.job == "generate_document"
    assert enqueued.kwargs == {"document_id": body["id"], "user_id": str(user.id)}
    # Con el momento en que pasó a `pending`: un reintento lleva otra clave.
    assert enqueued.key is not None
    assert enqueued.key.startswith(f"document:{body['id']}:")
    assert enqueued.max_attempts == 3


@pytest.mark.asyncio
async def test_the_snapshot_keeps_only_the_chosen_sections_and_items(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    await client.put(
        "/api/v1/profile", json={"full_name": "Ana", "summary": "Resumen largo"}
    )
    kept = await make_profile_entry(db_session, user.id, title="Se queda")
    dropped = await make_profile_entry(db_session, user.id, title="Se quita")
    await make_profile_entry(
        db_session, user.id, kind=EntryKind.EDUCATION, title="Grado"
    )
    await client.put(
        "/api/v1/profile/skills", json={"skills": [{"name": "SQL"}, {"name": "Go"}]}
    )
    skills = (await client.get("/api/v1/profile/skills")).json()
    go = next(skill for skill in skills if skill["name"] == "Go")

    response = await client.post(
        URL,
        json={
            "design": "classic",
            "language": "en",
            "name": "Mi CV",
            "sections": ["experience", "skills"],
            "excluded_ids": [str(dropped.id), go["id"]],
        },
    )

    assert response.status_code == 202
    assert response.json()["name"] == "Mi CV"
    content = (await _document(db_session, response.json()["id"])).content
    assert content is not None
    assert content["summary"] is None
    assert [s["section"] for s in content["entry_sections"]] == ["experience"]
    assert [e["id"] for e in content["entry_sections"][0]["entries"]] == [str(kept.id)]
    assert [skill["name"] for skill in content["skills"]] == ["SQL"]


@pytest.mark.asyncio
async def test_another_users_profile_never_reaches_the_snapshot(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    queue: InMemoryJobQueue,
):
    # Aislamiento (invariante 1): la foto sale solo de las filas del usuario, y un
    # id ajeno en la selección no tiene ningún efecto.
    others = await make_profile_entry(db_session, other_user.id, title="Ajena")
    mine = await make_profile_entry(db_session, user.id, title="Mía")

    response = await client.post(
        URL,
        json={"design": "classic", "language": "es", "excluded_ids": [str(others.id)]},
    )

    content = (await _document(db_session, response.json()["id"])).content
    assert content is not None
    titles = [e["title"] for s in content["entry_sections"] for e in s["entries"]]
    assert titles == [mine.title]


@pytest.mark.asyncio
async def test_an_empty_profile_can_be_generated(
    client: AsyncClient, queue: InMemoryJobQueue
):
    response = await client.post(URL, json={"design": "graphic", "language": "en"})

    assert response.status_code == 202
    # El nombre por defecto, en el idioma del CV.
    assert response.json()["name"] == "CV Graphic"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"design": "../classic", "language": "es"}, "unknown_design"),
        ({"design": "nope", "language": "es"}, "unknown_design"),
        ({"design": "classic", "language": "fr"}, "design_language_unavailable"),
    ],
)
async def test_an_unknown_design_or_language_is_rejected_before_creating_anything(
    client: AsyncClient,
    db_session: AsyncSession,
    queue: InMemoryJobQueue,
    payload: dict[str, str],
    code: str,
):
    response = await client.post(URL, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == code
    assert await db_session.scalar(select(Document.id)) is None
    assert queue.jobs == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"design": "classic", "language": "ES"},
        {"design": "classic", "language": "es", "sections": ["photo"]},
        {"design": "classic", "language": "es", "excluded_ids": ["no-es-un-id"]},
        {"design": "", "language": "es"},
    ],
)
async def test_a_malformed_request_is_a_422(
    client: AsyncClient, queue: InMemoryJobQueue, payload: dict[str, object]
):
    response = await client.post(URL, json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_the_document_limit_counts_pending_ones(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    await LimitService(db_session).set_override(user.id, LimitKey.DOCUMENTS, 1)
    first = await client.post(URL, json={"design": "classic", "language": "es"})

    second = await client.post(URL, json={"design": "classic", "language": "es"})

    assert first.status_code == 202
    assert second.status_code == 409
    assert (second.json()["code"], second.json()["used"]) == (
        "documents_limit_reached",
        1,
    )
    assert len(queue.jobs) == 1


@pytest.mark.asyncio
async def test_a_full_storage_rejects_generating(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    # El tamaño no se sabe hasta maquetar; con el almacenamiento lleno no hay
    # nada que esperar del worker.
    await make_document(db_session, user.id, size_bytes=1_000)
    await LimitService(db_session).set_override(user.id, LimitKey.STORAGE_BYTES, 1_000)

    response = await client.post(URL, json={"design": "classic", "language": "es"})

    assert response.status_code == 409
    assert response.json()["code"] == "storage_limit_reached"
    assert queue.jobs == []


@pytest.mark.asyncio
async def test_a_queue_down_still_answers_202_and_leaves_the_row_pending(
    client: AsyncClient, db_session: AsyncSession
):
    # Encolar falla después del commit (segundo plano §2): la fila ya existe y el
    # barrido de pendientes la reencola. Un 500 haría reintentar al usuario y
    # dejaría dos CVs.
    class DownQueue(InMemoryJobQueue):
        async def enqueue(self, job: str, **kwargs: JobArg) -> bool:  # type: ignore[override]
            raise QueueUnavailableError("valkey caído")

    app.dependency_overrides[get_job_queue] = DownQueue
    try:
        response = await client.post(URL, json={"design": "classic", "language": "es"})
    finally:
        app.dependency_overrides.pop(get_job_queue, None)

    assert response.status_code == 202
    document = await _document(db_session, response.json()["id"])
    assert document.status == "pending"


@pytest.mark.asyncio
async def test_generating_is_rate_limited_per_user_apart_from_uploads(
    client: AsyncClient, queue: InMemoryJobQueue
):
    app.state.rate_limiter = LimitsRateLimiter("async+memory://")
    try:
        for _ in range(30):
            ok = await client.post(URL, json={"design": "classic", "language": "es"})
            assert ok.status_code == 202

        response = await client.post(URL, json={"design": "classic", "language": "es"})
    finally:
        app.state.rate_limiter = DisabledRateLimiter()

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_an_unverified_email_cannot_generate(
    real_auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # RF-06: generar tiene coste. Con correo configurado (sin él no se exige, 0013).
    monkeypatch.setattr(settings, "smtp_host", "mailpit")
    signup = await real_auth_client.post(
        "/auth/signup",
        json=form(email=f"cv-{uuid.uuid4()}@example.com", password=PASSWORD),
        headers={"rid": "emailpassword"},
    )
    assert signup.json()["status"] == "OK"

    response = await real_auth_client.post(
        URL, json={"design": "classic", "language": "es"}
    )
    designs = await real_auth_client.get(DESIGNS_URL)

    assert response.status_code == 403
    assert response.json()["code"] == "email_not_verified"
    assert designs.status_code == 200


@pytest.mark.asyncio
async def test_retry_puts_a_failed_cv_back_to_pending(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    created = await client.post(URL, json={"design": "classic", "language": "es"})
    document = await _document(db_session, created.json()["id"])
    document.status, document.error_code = "failed", "render_failed"
    await db_session.flush()

    response = await client.post(f"/api/v1/documents/{document.id}/retry")

    assert response.status_code == 202
    assert (response.json()["status"], response.json()["error_code"]) == (
        "pending",
        None,
    )
    assert len(queue.jobs) == 2


@pytest.mark.asyncio
async def test_a_document_that_has_not_failed_cannot_be_retried(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    uploaded = await make_document(db_session, user.id)

    response = await client.post(f"/api/v1/documents/{uploaded.id}/retry")

    assert response.status_code == 409
    assert response.json()["code"] == "document_not_failed"
    assert queue.jobs == []
