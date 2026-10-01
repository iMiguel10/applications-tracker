"""Tablero de solicitudes (F16, RF-120…122, A41)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.application import BOARD_COLUMN_LIMIT
from app.domain.application_status import ALLOWED_TRANSITIONS, ApplicationStatus
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company, make_status_change

URL = "/api/v1/applications/board"


def _column(body: dict, status: str) -> dict:
    return next(column for column in body["columns"] if column["status"] == status)


@pytest.mark.asyncio
async def test_an_empty_board_has_every_column_in_process_order(client: AsyncClient):
    response = await client.get(URL)

    assert response.status_code == 200
    columns = response.json()["columns"]
    assert [column["status"] for column in columns] == [
        s.value for s in ApplicationStatus
    ]
    for column in columns:
        assert (column["total"], column["items"]) == (0, [])
        assert column["allowed_transitions"] == [
            s.value for s in ALLOWED_TRANSITIONS[ApplicationStatus(column["status"])]
        ]


@pytest.mark.asyncio
async def test_cards_are_grouped_by_status_with_their_company(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    acme = await make_company(db_session, user.id, "Acme")
    saved = await make_application(
        db_session,
        user.id,
        acme,
        position_title="Guardada",
        status="saved",
        applied_at=None,
    )
    applied = await make_application(
        db_session, user.id, acme, position_title="Enviada"
    )

    body = (await client.get(URL)).json()

    [saved_card] = _column(body, "saved")["items"]
    [applied_card] = _column(body, "applied")["items"]
    assert (saved_card["id"], saved_card["position_title"]) == (
        str(saved.id),
        "Guardada",
    )
    assert applied_card["id"] == str(applied.id)
    assert applied_card["company"] == {"id": str(acme.id), "name": "Acme"}
    assert (_column(body, "saved")["total"], _column(body, "applied")["total"]) == (
        1,
        1,
    )


@pytest.mark.asyncio
async def test_status_since_is_the_last_change_by_seq_not_by_date(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Invariante 3: el último cambio es el de `seq` más alto. El inicial (de la
    # factoría) lleva la fecha de ahora y el último, una fecha anterior que declaró
    # el usuario: ordenar por fecha daría la del inicial.
    declared = datetime(2026, 9, 15, 10, tzinfo=UTC)
    application = await make_application(db_session, user.id, status="screening")
    await make_status_change(
        db_session, application, "screening", from_status="applied", changed_at=declared
    )

    body = (await client.get(URL)).json()

    [card] = _column(body, "screening")["items"]
    assert datetime.fromisoformat(card["status_since"]) == declared


@pytest.mark.asyncio
async def test_a_column_brings_the_first_cards_newest_in_status_first_and_the_total(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for day in range(BOARD_COLUMN_LIMIT + 2):
        application = await make_application(
            db_session,
            user.id,
            company,
            position_title=f"P{day}",
            status="saved",
            applied_at=None,
        )
        await make_status_change(
            db_session, application, "saved", changed_at=start + timedelta(days=day)
        )

    column = _column((await client.get(URL)).json(), "saved")

    assert column["total"] == BOARD_COLUMN_LIMIT + 2
    assert len(column["items"]) == BOARD_COLUMN_LIMIT
    titles = [card["position_title"] for card in column["items"]]
    assert titles[:2] == [f"P{BOARD_COLUMN_LIMIT + 1}", f"P{BOARD_COLUMN_LIMIT}"]
    assert "P0" not in titles and "P1" not in titles


@pytest.mark.asyncio
async def test_archived_applications_are_not_on_the_board(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id, archived_at=datetime.now(UTC))

    body = (await client.get(URL)).json()

    assert sum(column["total"] for column in body["columns"]) == 0


@pytest.mark.asyncio
async def test_the_list_filters_apply_to_the_board(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    acme = await make_company(db_session, user.id, "Acme")
    other = await make_company(db_session, user.id, "Globex")
    await make_application(db_session, user.id, acme, position_title="Backend Go")
    await make_application(db_session, user.id, other, position_title="Backend Py")
    await make_application(
        db_session,
        user.id,
        acme,
        position_title="Frontend",
        status="saved",
        applied_at=None,
    )

    by_search = (await client.get(URL, params={"q": "backend"})).json()
    by_company = (await client.get(URL, params={"company_id": str(acme.id)})).json()
    by_status = (await client.get(URL, params={"status": "saved"})).json()
    by_date = (
        await client.get(URL, params={"applied_from": date(2026, 10, 1).isoformat()})
    ).json()

    assert _column(by_search, "applied")["total"] == 2
    assert _column(by_search, "saved")["total"] == 0
    assert _column(by_company, "applied")["total"] == 1
    assert _column(by_company, "saved")["total"] == 1
    # Un filtro de estado deja las demás columnas vacías, pero siguen saliendo.
    assert len(by_status["columns"]) == len(ApplicationStatus)
    assert [c["status"] for c in by_status["columns"] if c["total"]] == ["saved"]
    assert sum(column["total"] for column in by_date["columns"]) == 0


@pytest.mark.asyncio
async def test_an_inverted_date_range_is_a_422(client: AsyncClient):
    response = await client.get(
        URL, params={"applied_from": "2026-10-01", "applied_to": "2026-09-01"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_another_users_applications_never_reach_the_board(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    others_company = await make_company(db_session, other_user.id)
    await make_application(db_session, other_user.id, others_company)
    # Su empresa como filtro tampoco descubre nada (invariante 1).
    body = (await client.get(URL, params={"company_id": str(others_company.id)})).json()
    unfiltered = (await client.get(URL)).json()

    assert sum(column["total"] for column in body["columns"]) == 0
    assert sum(column["total"] for column in unfiltered["columns"]) == 0
