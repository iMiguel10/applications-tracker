"""Habilidades e idiomas del perfil (F14, RF-102)."""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from app.domain.profile import MAX_LANGUAGES, MAX_SKILLS
from app.schemas.user import CurrentUser

SKILLS = "/api/v1/profile/skills"
LANGUAGES = "/api/v1/profile/languages"


async def _put_skills(client: AsyncClient, skills: list[dict[str, Any]]) -> Any:
    return await client.put(SKILLS, json={"skills": skills})


def _names(skills: list[dict[str, Any]]) -> list[str]:
    return [skill["name"] for skill in skills]


@pytest.mark.asyncio
async def test_a_new_profile_has_no_skills_or_languages(client: AsyncClient):
    assert (await client.get(SKILLS)).json() == []
    assert (await client.get(LANGUAGES)).json() == []


@pytest.mark.asyncio
async def test_saving_skills_keeps_their_order_and_fields(client: AsyncClient):
    response = await _put_skills(
        client,
        [
            {"name": "Python", "category": "Lenguajes", "level": "expert"},
            {"name": "  PostgreSQL ", "category": "", "level": None},
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert [(s["name"], s["category"], s["level"]) for s in body] == [
        ("Python", "Lenguajes", "expert"),
        ("PostgreSQL", None, None),
    ]
    assert (await client.get(SKILLS)).json() == body


@pytest.mark.asyncio
async def test_saving_again_keeps_ids_reorders_and_deletes_what_is_missing(
    client: AsyncClient,
):
    # F15 referencia las habilidades por id: guardar la lista no debe cambiárselo
    # a las que siguen.
    python, sql, docker = (
        await _put_skills(
            client, [{"name": "Python"}, {"name": "SQL"}, {"name": "Docker"}]
        )
    ).json()

    response = await _put_skills(
        client,
        [
            {"id": docker["id"], "name": "Docker"},
            {"id": python["id"], "name": "Python 3"},
            {"name": "Kubernetes"},
        ],
    )

    body = response.json()
    assert _names(body) == ["Docker", "Python 3", "Kubernetes"]
    assert body[0]["id"] == docker["id"]
    assert body[1]["id"] == python["id"]
    assert sql["id"] not in {skill["id"] for skill in body}


@pytest.mark.asyncio
async def test_two_skills_can_swap_names(client: AsyncClient):
    # El índice único se comprueba fila a fila: sin el nombre provisional, el
    # primer UPDATE chocaría con el nombre que aún tiene la otra fila.
    a, b = (await _put_skills(client, [{"name": "A"}, {"name": "B"}])).json()

    response = await _put_skills(
        client, [{"id": a["id"], "name": "B"}, {"id": b["id"], "name": "A"}]
    )

    assert response.status_code == 200
    assert _names(response.json()) == ["B", "A"]


@pytest.mark.asyncio
async def test_a_removed_skill_can_come_back_with_other_capitals(client: AsyncClient):
    await _put_skills(client, [{"name": "React"}])

    response = await _put_skills(client, [{"name": "react"}])

    assert response.status_code == 200
    assert _names(response.json()) == ["react"]


@pytest.mark.asyncio
async def test_repeated_skill_names_are_rejected_ignoring_case(client: AsyncClient):
    await _put_skills(client, [{"name": "Go"}])

    response = await _put_skills(client, [{"name": "Python"}, {"name": "PYTHON"}])

    assert response.status_code == 422
    assert response.json()["code"] == "duplicate_skill"
    assert _names((await client.get(SKILLS)).json()) == ["Go"]


@pytest.mark.asyncio
async def test_a_skill_of_another_user_cannot_be_taken(
    client: AsyncClient,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
):
    as_user(other_user)
    [theirs] = (await _put_skills(client, [{"name": "Ajena"}])).json()
    as_user(user)

    response = await _put_skills(client, [{"id": theirs["id"], "name": "Mía"}])
    repeated = await _put_skills(client, [{"name": "X"}])
    [mine] = repeated.json()
    twice = await _put_skills(
        client, [{"id": mine["id"], "name": "X"}, {"id": mine["id"], "name": "Y"}]
    )

    assert response.status_code == 422
    assert response.json()["code"] == "skill_not_in_profile"
    assert twice.status_code == 422
    as_user(other_user)
    assert _names((await client.get(SKILLS)).json()) == ["Ajena"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "skills",
    [
        [{"name": ""}],
        [{"name": "x" * 101}],
        [{"name": "Python", "level": "guru"}],
        [{"name": f"S{index}"} for index in range(MAX_SKILLS + 1)],
    ],
)
async def test_invalid_skills_are_rejected(
    client: AsyncClient, skills: list[dict[str, Any]]
):
    assert (await _put_skills(client, skills)).status_code == 422


@pytest.mark.asyncio
async def test_languages_are_saved_with_their_level(client: AsyncClient):
    response = await client.put(
        LANGUAGES,
        json={
            "languages": [
                {"language": "Español", "level": "native"},
                {"language": "Inglés", "level": "c1"},
            ]
        },
    )

    assert response.status_code == 200
    assert [(item["language"], item["level"]) for item in response.json()] == [
        ("Español", "native"),
        ("Inglés", "c1"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("languages", "code"),
    [
        (
            [
                {"language": "Inglés", "level": "b2"},
                {"language": "inglés", "level": "c1"},
            ],
            "duplicate_language",
        ),
        ([{"language": "Inglés", "level": "c3"}], None),
        ([{"language": "Inglés"}], None),
        (
            [
                {"language": f"L{index}", "level": "a1"}
                for index in range(MAX_LANGUAGES + 1)
            ],
            None,
        ),
    ],
)
async def test_invalid_languages_are_rejected(
    client: AsyncClient, languages: list[dict[str, Any]], code: str | None
):
    response = await client.put(LANGUAGES, json={"languages": languages})

    assert response.status_code == 422
    if code:
        assert response.json()["code"] == code


@pytest.mark.asyncio
async def test_lists_never_include_other_users_items(
    client: AsyncClient,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
):
    as_user(other_user)
    await _put_skills(client, [{"name": "Ajena"}])
    await client.put(
        LANGUAGES, json={"languages": [{"language": "Ajeno", "level": "a1"}]}
    )
    as_user(user)

    assert (await client.get(SKILLS)).json() == []
    assert (await client.get(LANGUAGES)).json() == []
