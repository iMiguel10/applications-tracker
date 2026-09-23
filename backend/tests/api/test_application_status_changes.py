from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import CurrentUser
from tests.factories import make_application, make_status_change


@pytest.mark.asyncio
async def test_created_application_exposes_its_allowed_transitions(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")

    response = await client.get(f"/api/v1/applications/{application.id}")

    assert response.json()["allowed_transitions"] == [
        "screening",
        "interviewing",
        "rejected",
        "withdrawn",
    ]


@pytest.mark.asyncio
async def test_final_status_has_no_allowed_transitions(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(
        db_session, user.id, status="rejected", applied_at=date(2026, 9, 1)
    )

    response = await client.get(f"/api/v1/applications/{application.id}")

    assert response.json()["allowed_transitions"] == []


@pytest.mark.asyncio
async def test_change_status_returns_the_updated_application(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")

    response = await client.post(
        f"/api/v1/applications/{application.id}/status-changes",
        json={"to_status": "screening", "note": "Prueba técnica el jueves"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "screening"
    assert body["allowed_transitions"] == ["interviewing", "rejected", "withdrawn"]


@pytest.mark.asyncio
async def test_invalid_transition_is_409_with_a_stable_code(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="saved")

    response = await client.post(
        f"/api/v1/applications/{application.id}/status-changes",
        json={"to_status": "interviewing"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "invalid_transition"


@pytest.mark.asyncio
async def test_changed_at_without_timezone_is_422(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")

    response = await client.post(
        f"/api/v1/applications/{application.id}/status-changes",
        json={"to_status": "screening", "changed_at": "2026-09-10T10:00:00"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_history_is_most_recent_first(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="saved")
    await make_status_change(db_session, application, to_status="applied")

    response = await client.get(
        f"/api/v1/applications/{application.id}/status-changes"
    )

    assert response.status_code == 200
    body = response.json()
    assert [change["to_status"] for change in body] == ["applied", "saved"]
    assert body[-1]["from_status"] is None


@pytest.mark.asyncio
async def test_undo_last_restores_the_previous_status(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")
    await client.post(
        f"/api/v1/applications/{application.id}/status-changes",
        json={"to_status": "screening"},
    )

    response = await client.delete(
        f"/api/v1/applications/{application.id}/status-changes/last"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"


@pytest.mark.asyncio
async def test_undo_the_initial_change_is_409(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="applied")

    response = await client.delete(
        f"/api/v1/applications/{application.id}/status-changes/last"
    )

    assert response.status_code == 409
    assert response.json()["code"] == "cannot_undo_initial_change"


@pytest.mark.asyncio
async def test_undo_removes_the_last_by_seq_not_by_changed_at(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Registrar un cambio con changed_at pasado y deshacer debe quitar ESE cambio
    # (el último insertado), no el que declara la fecha más reciente (0004).
    application = await make_application(db_session, user.id, status="saved")
    now = datetime.now(UTC)
    await make_status_change(db_session, application, to_status="applied", changed_at=now)
    application.status = "applied"
    await make_status_change(
        db_session,
        application,
        to_status="withdrawn",
        changed_at=now - timedelta(days=2),
    )
    application.status = "withdrawn"
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/applications/{application.id}/status-changes/last"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
