from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import CurrentUser
from tests.factories import make_application, make_interview


@pytest.mark.asyncio
async def test_create_interview_returns_full_resource(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)

    response = await client.post(
        f"/api/v1/applications/{application.id}/interviews",
        json={
            "scheduled_at": "2026-10-01T10:00:00Z",
            "duration_minutes": 45,
            "interviewers": "Laura (RR. HH.)",
            "interview_type": "hr",
            "format": "online",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["outcome"] == "pending"
    assert body["duration_minutes"] == 45


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"duration_minutes": 0},
        {"interview_type": "onboarding"},
        {"format": "carrier_pigeon"},
    ],
    ids=["zero_duration", "unknown_type", "unknown_format"],
)
async def test_invalid_interview_is_422(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    overrides: dict[str, object],
):
    application = await make_application(db_session, user.id)
    payload = {"scheduled_at": "2026-10-01T10:00:00Z"} | overrides

    response = await client.post(
        f"/api/v1/applications/{application.id}/interviews", json=payload
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_is_ordered_by_scheduled_at(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    await make_interview(
        db_session, application, scheduled_at=datetime(2026, 11, 1, 10, tzinfo=UTC)
    )
    await make_interview(
        db_session, application, scheduled_at=datetime(2026, 10, 1, 10, tzinfo=UTC)
    )

    response = await client.get(f"/api/v1/applications/{application.id}/interviews")

    assert response.status_code == 200
    scheduled = [item["scheduled_at"] for item in response.json()]
    assert scheduled == sorted(scheduled)


@pytest.mark.asyncio
async def test_update_sets_the_outcome(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    interview = await make_interview(db_session, application)

    response = await client.patch(
        f"/api/v1/applications/{application.id}/interviews/{interview.id}",
        json={"outcome": "passed"},
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "passed"


@pytest.mark.asyncio
async def test_delete_interview(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    interview = await make_interview(db_session, application)

    response = await client.delete(
        f"/api/v1/applications/{application.id}/interviews/{interview.id}"
    )
    listed = await client.get(f"/api/v1/applications/{application.id}/interviews")

    assert response.status_code == 204
    assert listed.json() == []
