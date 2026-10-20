"""`GET /me/export` (issue #4): el `.zip` de la cuenta de la sesión, solo con lo suyo,
y con su propio rate limit."""

import io
import json
import zipfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_file_storage
from app.infra.rate_limit import DisabledRateLimiter, LimitsRateLimiter
from app.infra.storage import LocalFileStorage
from app.main import app
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_document

URL = "/api/v1/me/export"


@pytest.fixture(autouse=True)
def _storage(tmp_path: Path) -> Iterator[None]:
    app.dependency_overrides[get_file_storage] = lambda: LocalFileStorage(tmp_path)
    yield
    app.dependency_overrides.pop(get_file_storage, None)


@pytest.fixture
def limiter() -> Iterator[LimitsRateLimiter]:
    limiter = LimitsRateLimiter("async+memory://")
    app.state.rate_limiter = limiter
    yield limiter
    app.state.rate_limiter = DisabledRateLimiter()


async def _chunks(data: bytes) -> AsyncIterator[bytes]:
    yield data


@pytest.mark.asyncio
async def test_downloads_a_zip_with_only_this_account(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    tmp_path: Path,
) -> None:
    mine = await make_application(db_session, user.id, position_title="Mía")
    await make_application(db_session, other_user.id, position_title="Ajena")
    document = await make_document(db_session, user.id, name="CV.pdf")
    foreign = await make_document(db_session, other_user.id, name="ajeno.pdf")
    storage = LocalFileStorage(tmp_path)
    await storage.put(document.storage_key or "", _chunks(b"%PDF-1 mio"))
    await storage.put(foreign.storage_key or "", _chunks(b"%PDF-1 ajeno"))

    response = await client.get(URL)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="applications-tracker-export-')
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    applications = json.loads(archive.read("applications.json"))
    assert [a["id"] for a in applications] == [str(mine.id)]
    documents = [n for n in archive.namelist() if n.startswith("documents/")]
    assert documents == [f"documents/{document.id}-CV.pdf"]
    assert b"ajeno" not in response.content


@pytest.mark.asyncio
async def test_sixth_export_in_an_hour_is_429(
    client: AsyncClient, limiter: LimitsRateLimiter
) -> None:
    codes = [(await client.get(URL)).status_code for _ in range(6)]

    assert codes == [200] * 5 + [429]


@pytest.mark.asyncio
async def test_requires_a_session(anonymous_client: AsyncClient) -> None:
    assert (await anonymous_client.get(URL)).status_code == 401
