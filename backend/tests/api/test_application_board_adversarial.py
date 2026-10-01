"""Pruebas adversas del tablero (F16, RF-120…122): aislamiento, archivadas,
límite por columna, `status_since` tras deshacer y validación de parámetros."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.application import BOARD_COLUMN_LIMIT
from app.domain.application_status import ApplicationStatus
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company, make_status_change

URL = "/api/v1/applications/board"


def _column(body: dict, status: str) -> dict:
    return next(column for column in body["columns"] if column["status"] == status)


def _all_ids(body: dict) -> set[str]:
    return {card["id"] for column in body["columns"] for card in column["items"]}


def _grand_total(body: dict) -> int:
    return sum(column["total"] for column in body["columns"])


@pytest.mark.asyncio
async def test_other_users_cards_in_the_same_status_do_not_mix_with_mine(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    mine = await make_application(db_session, user.id, status="applied")
    for _ in range(3):
        await make_application(db_session, other_user.id, status="applied")

    body = (await client.get(URL)).json()

    assert _column(body, "applied")["total"] == 1
    assert _all_ids(body) == {str(mine.id)}


@pytest.mark.asyncio
async def test_filtering_by_another_users_company_returns_an_empty_board(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    # El usuario tiene sus propias solicitudes: un filtro por la empresa ajena no
    # debe ignorarse (devolviendo las mías) ni descubrir las del otro.
    await make_application(db_session, user.id)
    others_company = await make_company(db_session, other_user.id)
    await make_application(db_session, other_user.id, others_company)

    response = await client.get(URL, params={"company_id": str(others_company.id)})

    assert response.status_code == 200
    body = response.json()
    assert len(body["columns"]) == len(ApplicationStatus)
    assert _grand_total(body) == 0
    assert _all_ids(body) == set()


@pytest.mark.asyncio
async def test_archived_never_appear_even_if_the_list_archived_param_is_sent(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    active = await make_application(db_session, user.id)
    await make_application(db_session, user.id, archived_at=datetime.now(UTC))

    for archived in ("all", "archived"):
        body = (await client.get(URL, params={"archived": archived})).json()
        assert _all_ids(body) == {str(active.id)}, archived
        assert _grand_total(body) == 1, archived


@pytest.mark.asyncio
async def test_archived_cards_do_not_take_a_slot_nor_count_in_the_total(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for day in range(BOARD_COLUMN_LIMIT):
        application = await make_application(
            db_session, user.id, company, status="saved", applied_at=None
        )
        await make_status_change(
            db_session, application, "saved", changed_at=start + timedelta(days=day)
        )
    # Archivada y "más reciente en su estado" que todas: si contara, desplazaría
    # a una activa de las 50 primeras.
    archived = await make_application(
        db_session,
        user.id,
        company,
        status="saved",
        applied_at=None,
        archived_at=datetime.now(UTC),
    )
    await make_status_change(
        db_session, archived, "saved", changed_at=datetime(2026, 9, 30, tzinfo=UTC)
    )

    column = _column((await client.get(URL)).json(), "saved")

    assert column["total"] == BOARD_COLUMN_LIMIT
    assert len(column["items"]) == BOARD_COLUMN_LIMIT
    assert str(archived.id) not in {card["id"] for card in column["items"]}


@pytest.mark.asyncio
async def test_the_limit_applies_per_column_not_to_the_whole_board(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)
    for _ in range(BOARD_COLUMN_LIMIT + 1):
        await make_application(
            db_session, user.id, company, status="saved", applied_at=None
        )
    applied = [
        await make_application(db_session, user.id, company, status="applied")
        for _ in range(2)
    ]

    body = (await client.get(URL)).json()

    saved_column = _column(body, "saved")
    applied_column = _column(body, "applied")
    assert (saved_column["total"], len(saved_column["items"])) == (
        BOARD_COLUMN_LIMIT + 1,
        BOARD_COLUMN_LIMIT,
    )
    assert (applied_column["total"], len(applied_column["items"])) == (2, 2)
    assert {card["id"] for card in applied_column["items"]} == {
        str(a.id) for a in applied
    }


@pytest.mark.asyncio
async def test_truncated_column_is_stable_when_cards_tie_on_status_since(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Empate en la fecha: el desempate por id hace que dos lecturas devuelvan las
    # mismas 50 tarjetas en el mismo orden (nada "baila" al refrescar).
    company = await make_company(db_session, user.id)
    same_moment = datetime(2026, 9, 1, 12, tzinfo=UTC)
    for _ in range(BOARD_COLUMN_LIMIT + 5):
        application = await make_application(
            db_session, user.id, company, status="saved", applied_at=None
        )
        await make_status_change(
            db_session, application, "saved", changed_at=same_moment
        )

    first = _column((await client.get(URL)).json(), "saved")["items"]
    second = _column((await client.get(URL)).json(), "saved")["items"]

    assert [c["id"] for c in first] == [c["id"] for c in second]
    assert len(first) == BOARD_COLUMN_LIMIT


@pytest.mark.asyncio
async def test_after_undo_the_card_returns_with_status_since_of_the_previous_change_by_seq(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Historial: inicial `saved` (ahora) → `applied` declarado el 10-sep (seq
    # mayor, fecha menor) → `screening` por la API → deshacer. La tarjeta vuelve
    # a `applied` y su `status_since` es el 10-sep (último por seq), no la fecha
    # del inicial (que sería el "último" si se ordenara por fechas).
    declared = datetime(2026, 9, 10, 9, tzinfo=UTC)
    application = await make_application(
        db_session, user.id, status="saved", applied_at=None
    )
    await make_status_change(db_session, application, "applied", changed_at=declared)
    application.status = "applied"
    application.applied_at = declared.date()
    await db_session.flush()

    moved = await client.post(
        f"/api/v1/applications/{application.id}/status-changes",
        json={"to_status": "screening"},
    )
    assert moved.status_code == 201
    before_undo = (await client.get(URL)).json()
    undone = await client.delete(
        f"/api/v1/applications/{application.id}/status-changes/last"
    )
    assert undone.status_code == 200

    body = (await client.get(URL)).json()

    assert [c["id"] for c in _column(before_undo, "screening")["items"]] == [
        str(application.id)
    ]
    assert _column(body, "screening")["total"] == 0
    [card] = _column(body, "applied")["items"]
    assert card["id"] == str(application.id)
    assert datetime.fromisoformat(card["status_since"]) == declared


@pytest.mark.asyncio
async def test_combined_filters_are_intersected(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    acme = await make_company(db_session, user.id, "Acme")
    globex = await make_company(db_session, user.id, "Globex")
    target = await make_application(
        db_session,
        user.id,
        acme,
        position_title="Backend Go",
        work_mode="remote",
        source="linkedin",
    )
    # Cada una falla exactamente un filtro.
    await make_application(
        db_session,
        user.id,
        globex,
        position_title="Backend Go",
        work_mode="remote",
        source="linkedin",
    )
    await make_application(
        db_session,
        user.id,
        acme,
        position_title="Frontend",
        work_mode="remote",
        source="linkedin",
    )
    await make_application(
        db_session,
        user.id,
        acme,
        position_title="Backend Go",
        work_mode="onsite",
        source="linkedin",
    )
    await make_application(
        db_session,
        user.id,
        acme,
        position_title="Backend Go",
        work_mode="remote",
        source="referral",
    )
    await make_application(
        db_session,
        user.id,
        acme,
        position_title="Backend Go",
        status="saved",
        applied_at=None,
        work_mode="remote",
        source="linkedin",
    )

    response = await client.get(
        URL,
        params=[
            ("company_id", str(acme.id)),
            ("q", "backend"),
            ("work_mode", "remote"),
            ("source", "linkedin"),
            ("status", "applied"),
            ("status", "screening"),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert _all_ids(body) == {str(target.id)}
    assert _grand_total(body) == 1


@pytest.mark.asyncio
async def test_search_wildcards_are_literal_on_the_board(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id, position_title="Backend")

    body = (await client.get(URL, params={"q": "%"})).json()

    assert _grand_total(body) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"status": "not_a_status"},
        {"company_id": "not-a-uuid"},
        {"work_mode": "spaceship"},
        {"source": "carrier_pigeon"},
        {"applied_from": "2026-13-01"},
        {"q": "x" * 201},
    ],
    ids=["status", "company_id", "work_mode", "source", "date", "q_too_long"],
)
async def test_invalid_board_parameters_are_a_422(
    client: AsyncClient, params: dict[str, str]
):
    response = await client.get(URL, params=params)

    assert response.status_code == 422
