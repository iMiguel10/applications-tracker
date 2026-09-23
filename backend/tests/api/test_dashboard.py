import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import CurrentUser
from tests.factories import make_application


@pytest.mark.asyncio
async def test_dashboard_shape(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id, status="applied")

    response = await client.get("/api/v1/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert len(body["status_counts"]) == 8
    assert len(body["applications_per_week"]) == 12
    assert body["response_rate"]["sent_count"] == 1
    assert body["response_rate"]["rate"] is None
    assert body["upcoming_interviews"] == []
    assert body["pending_reminders"] == []
    assert body["stale_applications"] == []
    assert body["stale_after_days"] == 14


@pytest.mark.asyncio
async def test_dashboard_does_not_leak_another_users_data(
    client: AsyncClient, db_session: AsyncSession, other_user: CurrentUser
):
    await make_application(db_session, other_user.id, status="applied")

    response = await client.get("/api/v1/dashboard")

    body = response.json()
    assert sum(row["count"] for row in body["status_counts"]) == 0
