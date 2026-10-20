"""Aceptar los términos y la política de privacidad (issue #3): solo la versión
vigente, solo si la instalación los tiene, y queda en `GET /me`."""

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.legal import LEGAL_VERSION
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser

URL = "/api/v1/me/legal-acceptance"


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "legal_operator_name", "Ana García")
    monkeypatch.setattr(settings, "legal_contact_email", "privacidad@example.com")


@pytest.mark.asyncio
async def test_accepting_the_current_version_is_recorded(
    client: AsyncClient,
    user: CurrentUser,
    db_session: AsyncSession,
    configured: None,
) -> None:
    response = await client.post(URL, json={"version": LEGAL_VERSION})

    assert response.status_code == 204
    me = await client.get("/api/v1/me")
    assert me.json()["legal_accepted_version"] == LEGAL_VERSION
    row = await UserRepository(db_session).get_by_id(user.id)
    assert row is not None and row.legal_accepted_at is not None


@pytest.mark.asyncio
async def test_an_old_version_is_rejected(
    client: AsyncClient, configured: None
) -> None:
    # Una pantalla abierta desde antes de un cambio de versión no acepta la vieja.
    response = await client.post(URL, json={"version": "2020-01-01"})

    assert response.status_code == 409
    assert response.json()["code"] == "legal_version_outdated"
    me = await client.get("/api/v1/me")
    assert me.json()["legal_accepted_version"] is None


@pytest.mark.asyncio
async def test_nothing_to_accept_without_legal_texts(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "legal_operator_name", None)

    response = await client.post(URL, json={"version": LEGAL_VERSION})

    assert response.status_code == 409
    assert response.json()["code"] == "legal_not_configured"


@pytest.mark.asyncio
async def test_requires_a_session(anonymous_client: AsyncClient) -> None:
    response = await anonymous_client.post(URL, json={"version": LEGAL_VERSION})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_version_and_date_go_together(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # El CHECK de la BD: una versión sin fecha (o al revés) no se puede guardar.
    row = await UserRepository(db_session).get_by_id(user.id)
    assert row is not None
    row.legal_version = LEGAL_VERSION

    with pytest.raises(IntegrityError):
        await db_session.flush()
