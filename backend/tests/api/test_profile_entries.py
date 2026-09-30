"""Entradas del perfil: experiencia, formación, proyectos y certificaciones, con sus
logros (F14, RF-101, RF-102)."""

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LimitReachedError
from app.domain.profile import MAX_BULLETS_PER_ENTRY, MAX_ENTRIES, EntryKind
from app.models.profile_entry import ProfileEntryBullet
from app.repositories.user_repository import UserRepository
from app.schemas.profile import EntryCreate
from app.schemas.user import CurrentUser
from app.services.profile_entry_service import ProfileEntryService
from tests.conftest import create_test_user, test_engine
from tests.factories import make_profile_entry

URL = "/api/v1/profile/entries"
# Tiempo para que la segunda alta llegue a esperar el bloqueo del perfil.
LOCK_WAIT_SECONDS = 0.5

EXPERIENCE: dict[str, Any] = {
    "kind": "experience",
    "title": "Desarrolladora backend",
    "organization": "Acme",
    "location": "Madrid",
    "start_date": "2021-03-01",
    "end_date": None,
    "is_current": True,
    "description": "APIs de pagos.",
    "bullets": [
        {"text": "Migré los pagos a colas"},
        {"text": "Bajé la latencia un 40 %"},
    ],
}


def _titles(entries: list[dict[str, Any]], kind: str) -> list[str]:
    return [entry["title"] for entry in entries if entry["kind"] == kind]


@pytest.mark.asyncio
async def test_creating_an_entry_returns_it_with_its_bullets(client: AsyncClient):
    response = await client.post(URL, json=EXPERIENCE)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Desarrolladora backend"
    assert body["is_current"] is True
    assert [bullet["text"] for bullet in body["bullets"]] == [
        "Migré los pagos a colas",
        "Bajé la latencia un 40 %",
    ]
    assert all(bullet["id"] for bullet in body["bullets"])


@pytest.mark.asyncio
async def test_new_entries_go_to_the_end_of_their_section(client: AsyncClient):
    for title in ("Primera", "Segunda"):
        await client.post(URL, json=EXPERIENCE | {"title": title})
    await client.post(URL, json={"kind": "education", "title": "Grado"})

    entries = (await client.get(URL)).json()

    assert _titles(entries, "experience") == ["Primera", "Segunda"]
    assert _titles(entries, "education") == ["Grado"]


@pytest.mark.asyncio
async def test_editing_keeps_the_id_of_the_bullets_that_stay(client: AsyncClient):
    # F15 referencia los logros por id: editar la entrada no debe cambiárselo a los
    # que siguen en ella.
    created = (await client.post(URL, json=EXPERIENCE)).json()
    first, second = created["bullets"]

    response = await client.put(
        f"{URL}/{created['id']}",
        json=EXPERIENCE
        | {
            "bullets": [
                {"id": second["id"], "text": "Bajé la latencia un 45 %"},
                {"text": "Nuevo logro"},
            ]
        },
    )

    assert response.status_code == 200
    bullets = response.json()["bullets"]
    assert [bullet["text"] for bullet in bullets] == [
        "Bajé la latencia un 45 %",
        "Nuevo logro",
    ]
    assert bullets[0]["id"] == second["id"]
    assert first["id"] not in {bullet["id"] for bullet in bullets}


@pytest.mark.asyncio
async def test_a_bullet_of_another_entry_cannot_be_taken(
    client: AsyncClient, user: CurrentUser, db_session: AsyncSession
):
    other = await make_profile_entry(db_session, user.id, bullets=["Ajeno"])
    other_bullet_id = other.bullets[0].id
    created = (await client.post(URL, json=EXPERIENCE)).json()

    response = await client.put(
        f"{URL}/{created['id']}",
        json=EXPERIENCE | {"bullets": [{"id": str(other_bullet_id), "text": "Mío"}]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "bullet_not_in_entry"
    still = await db_session.scalar(
        select(ProfileEntryBullet.text).where(ProfileEntryBullet.id == other_bullet_id)
    )
    assert still == "Ajeno"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"is_current": True, "end_date": "2024-01-01"},
        {"is_current": False, "start_date": "2024-05-01", "end_date": "2024-01-01"},
        {"title": "   "},
        {"kind": "hobby"},
        {"bullets": [{"text": ""}]},
        {"bullets": [{"text": "x" * 501}]},
        {"bullets": [{"text": "Logro"}] * (MAX_BULLETS_PER_ENTRY + 1)},
        {"description": "x" * 2001},
    ],
)
async def test_invalid_entries_are_rejected(
    client: AsyncClient, changes: dict[str, Any]
):
    response = await client.post(URL, json=EXPERIENCE | changes)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_full_section_answers_409_with_its_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setitem(MAX_ENTRIES, EntryKind.CERTIFICATION, 2)
    certification = {"kind": "certification", "title": "AWS"}
    for _ in range(2):
        assert (await client.post(URL, json=certification)).status_code == 201

    response = await client.post(URL, json=certification)
    other_section = await client.post(URL, json={"kind": "project", "title": "Web"})

    assert response.status_code == 409
    assert response.json() | {"detail": None} == {
        "detail": None,
        "code": "profile_section_full",
        "limit": 2,
        "used": 2,
    }
    assert other_section.status_code == 201


@pytest.mark.asyncio
async def test_reordering_a_section(client: AsyncClient):
    ids = [
        (await client.post(URL, json=EXPERIENCE | {"title": title})).json()["id"]
        for title in ("A", "B", "C")
    ]

    response = await client.put(
        f"{URL}/order", json={"kind": "experience", "entry_ids": ids[::-1]}
    )

    assert response.status_code == 200
    assert _titles(response.json(), "experience") == ["C", "B", "A"]
    assert _titles((await client.get(URL)).json(), "experience") == ["C", "B", "A"]


@pytest.mark.asyncio
async def test_a_partial_or_foreign_order_is_rejected(
    client: AsyncClient,
    other_user: CurrentUser,
    db_session: AsyncSession,
):
    a, b = [
        (await client.post(URL, json=EXPERIENCE | {"title": title})).json()["id"]
        for title in ("A", "B")
    ]
    education = (
        await client.post(URL, json={"kind": "education", "title": "G"})
    ).json()
    theirs = await make_profile_entry(db_session, other_user.id)

    for entry_ids in (
        [a],
        [a, b, a],
        [a, b, education["id"]],
        [a, b, str(theirs.id)],
    ):
        response = await client.put(
            f"{URL}/order", json={"kind": "experience", "entry_ids": entry_ids}
        )
        assert response.status_code == 422, entry_ids
        assert response.json()["code"] == "entry_order_mismatch"

    assert _titles((await client.get(URL)).json(), "experience") == ["A", "B"]


@pytest.mark.asyncio
async def test_deleting_an_entry_deletes_its_bullets(
    client: AsyncClient, db_session: AsyncSession
):
    created = (await client.post(URL, json=EXPERIENCE)).json()

    response = await client.delete(f"{URL}/{created['id']}")

    assert response.status_code == 204
    assert (await client.get(URL)).json() == []
    remaining = await db_session.scalar(
        select(func.count()).select_from(ProfileEntryBullet)
    )
    assert remaining == 0


@pytest.mark.asyncio
async def test_lists_never_include_other_users_entries(
    client: AsyncClient,
    other_user: CurrentUser,
    db_session: AsyncSession,
):
    await make_profile_entry(db_session, other_user.id, title="Ajena")

    assert (await client.get(URL)).json() == []


@pytest.mark.asyncio
async def test_two_simultaneous_creates_cannot_overflow_a_section(
    monkeypatch: pytest.MonkeyPatch,
):
    # Dos transacciones reales con un hueco en la sección: la segunda espera al
    # bloqueo del perfil, ve la primera ya confirmada y se rechaza.
    monkeypatch.setitem(MAX_ENTRIES, EntryKind.PROJECT, 1)
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        await setup.commit()
    first = AsyncSession(test_engine, expire_on_commit=False)
    second = AsyncSession(test_engine, expire_on_commit=False)
    data = EntryCreate(kind=EntryKind.PROJECT, title="Web")
    try:
        await ProfileEntryService(first).profiles.get_or_create(owner.id)
        await first.commit()
        service = ProfileEntryService(first)
        profile = await service.profiles.get_or_create(owner.id)
        await service.profiles.lock(profile.id)
        waiting = asyncio.create_task(
            ProfileEntryService(second).create(owner.id, data)
        )
        await asyncio.sleep(LOCK_WAIT_SECONDS)
        assert not waiting.done(), "la segunda alta debería esperar al bloqueo"
        await make_profile_entry(first, owner.id, kind=EntryKind.PROJECT)
        await first.commit()

        with pytest.raises(LimitReachedError):
            await waiting
    finally:
        await first.close()
        await second.rollback()
        await second.close()
        async with AsyncSession(test_engine) as cleanup:
            await UserRepository(cleanup).delete(owner.id)
            await cleanup.commit()
