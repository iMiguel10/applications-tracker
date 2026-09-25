import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.limits import LimitKey
from app.schemas.user import CurrentUser
from app.services.limit_service import LimitService
from tests.factories import make_company


@pytest.mark.asyncio
async def test_usage_lists_every_limit_with_used_limit_and_remaining(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_company(db_session, user.id)
    await LimitService(db_session).set_override(user.id, LimitKey.COMPANIES, 10)

    response = await client.get("/api/v1/me/usage")

    assert response.status_code == 200
    body = response.json()
    assert body["warning_ratio"] == 0.8
    by_key = {item["key"]: item for item in body["limits"]}
    assert set(by_key) == {"applications", "companies", "reminders"}
    assert by_key["companies"] == {
        "key": "companies",
        "used": 1,
        "limit": 10,
        "remaining": 9,
        "renews": False,
    }
    assert by_key["applications"]["limit"] == settings.limit_applications


@pytest.mark.asyncio
async def test_creating_over_the_limit_says_which_and_how_much(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
):
    # L3 por la API: 409 con el código de siempre y los números (RF-142).
    monkeypatch.setattr(settings, "limit_companies", 1)
    await make_company(db_session, user.id)

    response = await client.post("/api/v1/companies", json={"name": "Otra"})

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "companies_limit_reached"
    assert body["limit"] == 1
    assert body["used"] == 1
    assert "detail" in body


@pytest.mark.asyncio
async def test_unlimited_is_null_limit_and_remaining(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await LimitService(db_session).set_override(user.id, LimitKey.APPLICATIONS, None)

    response = await client.get("/api/v1/me/usage")

    applications = next(
        item for item in response.json()["limits"] if item["key"] == "applications"
    )
    assert applications["limit"] is None
    assert applications["remaining"] is None
