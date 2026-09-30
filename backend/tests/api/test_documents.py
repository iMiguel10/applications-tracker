"""Biblioteca de documentos: subida y listado (RF-90, RF-94, ficheros §2 y §8)."""

import asyncio
import hashlib
import uuid
from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_file_storage
from app.core.config import settings
from app.core.exceptions import AppException
from app.domain.documents import DocumentKind
from app.domain.limits import LimitKey
from app.infra.rate_limit import DisabledRateLimiter, LimitsRateLimiter
from app.infra.storage import LocalFileStorage
from app.main import app
from app.models.document import Document
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.document_service import DocumentService
from app.services.limit_service import LimitService
from tests.auth_helpers import PASSWORD, form
from tests.conftest import create_test_user, test_engine
from tests.factories import make_document
from tests.pdf_helpers import make_pdf

URL = "/api/v1/documents"
PDF = {"Content-Type": "application/pdf"}


@pytest.fixture
def files_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture(autouse=True)
def _storage(files_root: Path) -> Iterator[None]:
    app.dependency_overrides[get_file_storage] = lambda: LocalFileStorage(files_root)
    yield
    app.dependency_overrides.pop(get_file_storage, None)


def _stored_files(root: Path) -> list[Path]:
    """Ficheros del almacén, sin contar los temporales."""
    return [
        path for path in root.rglob("*") if path.is_file() and ".tmp" not in path.parts
    ]


async def _upload(
    client: AsyncClient,
    content: bytes,
    *,
    kind: str = "cv",
    name: str | None = "cv.pdf",
) -> httpx.Response:
    params = {"kind": kind} | ({"name": name} if name is not None else {})
    return await client.post(URL, params=params, content=content, headers=PDF)


async def _chunks(content: bytes) -> AsyncIterator[bytes]:
    yield content


# --- Subida --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_stores_the_file_and_a_ready_row(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser, files_root: Path
):
    content = make_pdf(pages=2)

    response = await _upload(client, content, kind="cover_letter", name="Carta.pdf")

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "cover_letter"
    assert body["origin"] == "uploaded"
    assert body["status"] == "ready"
    assert body["name"] == "Carta.pdf"
    assert body["size_bytes"] == len(content)
    document = await db_session.get(Document, uuid.UUID(body["id"]))
    assert document is not None
    assert document.user_id == user.id
    assert document.sha256 == hashlib.sha256(content).hexdigest()
    # La ruta la genera el servidor con ids; el nombre original no llega al disco.
    assert document.storage_key == f"users/{user.id}/documents/{document.id}.pdf"
    assert (files_root / document.storage_key).read_bytes() == content


@pytest.mark.asyncio
async def test_the_name_is_sanitized_and_never_reaches_the_disk(
    client: AsyncClient, files_root: Path
):
    response = await _upload(client, make_pdf(), name="../../etc/passwd")

    assert response.status_code == 201
    assert response.json()["name"] == "passwd"
    [stored] = _stored_files(files_root)
    assert stored.name == f"{response.json()['id']}.pdf"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"hola, soy un .txt", id="texto"),
        pytest.param(b"%PDF-1.7\nesto no es un PDF", id="solo-la-firma"),
        pytest.param(make_pdf()[:200], id="cortado"),
        pytest.param(make_pdf(password="secreta"), id="con-contrasena"),
        pytest.param(b"", id="vacio"),
    ],
)
async def test_not_a_pdf_is_rejected_by_its_content(
    client: AsyncClient, db_session: AsyncSession, files_root: Path, content: bytes
):
    # D1: la extensión (el nombre dice .pdf) y el Content-Type no cuentan.
    response = await _upload(client, content, name="cv.pdf")

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file_type"
    assert _stored_files(files_root) == []
    assert await db_session.scalar(select(Document.id)) is None


@pytest.mark.asyncio
async def test_a_body_over_the_limit_is_cut_whatever_content_length_says(
    client: AsyncClient,
    db_session: AsyncSession,
    files_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    # D2: el cliente declara 1 KB y manda 6 MB. Se cuenta lo que llega y se corta
    # al pasarse, sin llegar a escribir nada.
    monkeypatch.setattr(settings, "document_max_bytes", 5 * 1024 * 1024)
    chunk = b"%PDF-" + b"0" * (64 * 1024 - 5)

    async def body() -> AsyncGenerator[bytes, None]:
        for _ in range(96):  # 6 MB
            yield chunk

    response = await client.post(
        URL,
        params={"kind": "cv"},
        content=body(),
        headers=PDF | {"Content-Length": "1024"},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"
    assert response.json()["max_bytes"] == 5 * 1024 * 1024
    assert _stored_files(files_root) == []
    assert await db_session.scalar(select(Document.id)) is None


@pytest.mark.asyncio
async def test_the_document_limit_counts_archived_ones(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser, files_root: Path
):
    await LimitService(db_session).set_override(user.id, LimitKey.DOCUMENTS, 1)
    await make_document(db_session, user.id, archived_at=None)

    response = await _upload(client, make_pdf())

    assert response.status_code == 409
    body = response.json()
    assert (body["code"], body["limit"], body["used"]) == (
        "documents_limit_reached",
        1,
        1,
    )
    assert _stored_files(files_root) == []


@pytest.mark.asyncio
async def test_the_storage_limit_counts_the_real_size(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser, files_root: Path
):
    content = make_pdf()
    await make_document(db_session, user.id, size_bytes=1_000)
    await LimitService(db_session).set_override(
        user.id, LimitKey.STORAGE_BYTES, 1_000 + len(content) - 1
    )

    response = await _upload(client, content)

    assert response.status_code == 409
    assert response.json()["code"] == "storage_limit_reached"
    assert response.json()["used"] == 1_000
    assert _stored_files(files_root) == []


@pytest.mark.asyncio
async def test_exactly_filling_the_storage_is_allowed(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    content = make_pdf()
    await LimitService(db_session).set_override(
        user.id, LimitKey.STORAGE_BYTES, len(content)
    )

    response = await _upload(client, content)

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_uploads_are_rate_limited_per_user(client: AsyncClient):
    # 30 por hora: la 31.ª espera, antes de leer el cuerpo.
    app.state.rate_limiter = LimitsRateLimiter("async+memory://")
    try:
        content = make_pdf()
        for _ in range(30):
            assert (await _upload(client, content)).status_code == 201

        response = await _upload(client, content)
    finally:
        app.state.rate_limiter = DisabledRateLimiter()

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert int(response.headers["Retry-After"]) > 0


# --- Listado -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_is_the_library_without_archived_newest_first(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    old = await make_document(db_session, user.id, name="viejo.pdf")
    new = await make_document(
        db_session, user.id, name="carta.pdf", kind="cover_letter"
    )
    archived = await make_document(
        db_session, user.id, name="archivado.pdf", archived_at=old.created_at
    )
    await make_document(db_session, other_user.id, name="ajeno.pdf")

    library = (await client.get(URL)).json()
    archived_only = (await client.get(URL, params={"archived": "true"})).json()
    cvs = (await client.get(URL, params={"kind": "cv"})).json()

    assert [item["id"] for item in library["items"]] == [str(new.id), str(old.id)]
    assert library["total"] == 2
    assert [item["id"] for item in archived_only["items"]] == [str(archived.id)]
    assert [item["id"] for item in cvs["items"]] == [str(old.id)]


# --- Verificación del email (contra el core real) ------------------------------


@pytest.mark.asyncio
async def test_an_unverified_email_cannot_upload_but_can_list(
    real_auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    # A38: subir tiene coste; listar, no. Con correo configurado (sin él no se
    # exige, 0013).
    monkeypatch.setattr(settings, "smtp_host", "mailpit")
    signup = await real_auth_client.post(
        "/auth/signup",
        json=form(email=f"docs-{uuid.uuid4()}@example.com", password=PASSWORD),
        headers={"rid": "emailpassword"},
    )
    assert signup.json()["status"] == "OK"

    upload = await _upload(real_auth_client, make_pdf())
    listing = await real_auth_client.get(URL)

    assert upload.status_code == 403
    assert upload.json()["code"] == "email_not_verified"
    assert listing.status_code == 200


# --- Carreras con transacciones reales -----------------------------------------


@pytest.mark.asyncio
async def test_two_simultaneous_uploads_cannot_exceed_the_storage_together(
    files_root: Path,
):
    # D3 (A30): cabe una, pero no las dos. Sin la fila del usuario bloqueada,
    # las dos verían el almacenamiento vacío y entrarían.
    content = make_pdf()
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        await LimitService(setup).set_override(
            owner.id, LimitKey.STORAGE_BYTES, len(content) * 3 // 2
        )
    storage = LocalFileStorage(files_root)
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

        assert sorted(results) == ["ok", "storage_limit_reached"]
        assert len(_stored_files(files_root)) == 1
    finally:
        await session_a.close()
        await session_b.close()
        async with AsyncSession(test_engine) as cleanup:
            await UserRepository(cleanup).delete(owner.id)
            await cleanup.commit()
