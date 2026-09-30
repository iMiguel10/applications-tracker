"""Perfil profesional: datos básicos (F14, RF-100)."""

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.profile import MAX_LINKS, SUMMARY_MAX_LENGTH
from app.models.profile import Profile
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from tests.conftest import create_test_user, test_engine

URL = "/api/v1/profile"
# Tiempo para que la segunda inserción llegue a esperar el bloqueo de la primera.
LOCK_WAIT_SECONDS = 0.5

EMPTY_PROFILE: dict[str, Any] = {
    "full_name": None,
    "headline": None,
    "contact_email": None,
    "phone": None,
    "location": None,
    "links": [],
    "summary": None,
}

FULL_PROFILE: dict[str, Any] = {
    "full_name": "Ana García",
    "headline": "Desarrolladora backend",
    "contact_email": "ana@example.com",
    "phone": "+34 600 000 000",
    "location": "Madrid, España",
    "links": [
        {"label": "LinkedIn", "url": "https://www.linkedin.com/in/ana"},
        {"label": "GitHub", "url": "https://github.com/ana"},
    ],
    "summary": "Diez años construyendo APIs.",
}


async def _profile_rows(session: AsyncSession, user_id: object) -> int:
    total = await session.scalar(
        select(func.count()).select_from(Profile).where(Profile.user_id == user_id)
    )
    return total or 0


@pytest.mark.asyncio
async def test_a_profile_never_saved_is_empty_and_reading_it_creates_nothing(
    client: AsyncClient, user: CurrentUser, db_session: AsyncSession
):
    response = await client.get(URL)

    assert response.status_code == 200
    assert response.json() == EMPTY_PROFILE
    assert await _profile_rows(db_session, user.id) == 0


@pytest.mark.asyncio
async def test_saving_the_profile_stores_it_and_returns_it(client: AsyncClient):
    saved = await client.put(URL, json=FULL_PROFILE)
    read = await client.get(URL)

    assert saved.status_code == 200
    assert saved.json() == FULL_PROFILE
    assert read.json() == FULL_PROFILE


@pytest.mark.asyncio
async def test_saving_replaces_everything_and_blank_fields_become_null(
    client: AsyncClient, user: CurrentUser, db_session: AsyncSession
):
    await client.put(URL, json=FULL_PROFILE)

    response = await client.put(
        URL, json={"full_name": "  Ana  ", "headline": "   ", "phone": ""}
    )

    assert response.status_code == 200
    assert response.json() == EMPTY_PROFILE | {"full_name": "Ana"}
    # Sigue siendo una sola fila: guardar actualiza, no inserta otra.
    assert await _profile_rows(db_session, user.id) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://example.com",
        "//example.com",
        "/profile",
        "https://",
        "linkedin.com/in/ana",
    ],
)
async def test_links_only_accept_http_and_https_with_a_host(
    client: AsyncClient, url: str
):
    # Se pintan como <a href> en la interfaz y en el PDF: `javascript:` sería un
    # XSS en la aplicación.
    response = await client.put(URL, json={"links": [{"label": "Web", "url": url}]})

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"contact_email": "no-es-un-email"},
        {"phone": "600 000 000; DROP"},
        {"summary": "x" * (SUMMARY_MAX_LENGTH + 1)},
        {"full_name": "x" * 201},
        {"links": [{"label": "", "url": "https://example.com"}]},
        {"links": [{"label": "Web", "url": "https://example.com"}] * (MAX_LINKS + 1)},
    ],
)
async def test_invalid_profile_data_is_rejected(
    client: AsyncClient, payload: dict[str, Any]
):
    response = await client.put(URL, json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_each_user_sees_and_edits_only_their_own_profile(
    client: AsyncClient,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Any,
    db_session: AsyncSession,
):
    await client.put(URL, json=FULL_PROFILE)

    as_user(other_user)
    theirs = await client.get(URL)
    await client.put(URL, json={"full_name": "Otra persona"})
    as_user(user)
    mine = await client.get(URL)

    assert theirs.json() == EMPTY_PROFILE
    assert mine.json() == FULL_PROFILE
    assert await _profile_rows(db_session, other_user.id) == 1


@pytest.mark.asyncio
async def test_two_simultaneous_first_saves_create_a_single_profile():
    # Dos transacciones reales. La segunda inserción espera a que la primera
    # confirme; sin ON CONFLICT chocaría entonces con la clave única de user_id y
    # respondería 500.
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        await setup.commit()
    first = AsyncSession(test_engine)
    second = AsyncSession(test_engine)
    try:
        await ProfileRepository(first).get_or_create(owner.id)
        waiting = asyncio.create_task(ProfileRepository(second).get_or_create(owner.id))
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not waiting.done(), "la segunda debería esperar a la primera"
        await first.commit()
        await waiting
        await second.commit()

        async with AsyncSession(test_engine) as check:
            assert await _profile_rows(check, owner.id) == 1
    finally:
        await first.close()
        await second.close()
        async with AsyncSession(test_engine) as cleanup:
            await UserRepository(cleanup).delete(owner.id)
            await cleanup.commit()
