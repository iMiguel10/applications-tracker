import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_user_service
from app.main import app
from app.repositories.identity_repository import IdentityRepository
from app.schemas.user import CurrentUser
from app.services.user_service import UserService


class FakeIdentities(IdentityRepository):
    """Sustituye a SuperTokens: el test no necesita red ni core."""

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return f"{supertokens_user_id}@example.com"


@pytest.mark.asyncio
async def test_me_returns_own_id_and_email_from_identity_store(
    client: AsyncClient, user: CurrentUser, db_session: AsyncSession
):
    app.dependency_overrides[get_user_service] = lambda: UserService(
        db_session, identities=FakeIdentities()
    )

    response = await client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "email": f"{user.supertokens_user_id}@example.com",
    }


@pytest.mark.asyncio
async def test_preferences_default_to_no_language_and_14_days(
    client: AsyncClient, user: CurrentUser
):
    response = await client.get("/api/v1/me/preferences")

    assert response.status_code == 200
    assert response.json() == {"language": None, "stale_after_days": 14}


@pytest.mark.asyncio
async def test_updating_preferences_only_changes_sent_fields(
    client: AsyncClient, user: CurrentUser
):
    first = await client.patch("/api/v1/me/preferences", json={"language": "en"})
    assert first.json() == {"language": "en", "stale_after_days": 14}

    second = await client.patch("/api/v1/me/preferences", json={"stale_after_days": 30})
    assert second.json() == {"language": "en", "stale_after_days": 30}


@pytest.mark.asyncio
async def test_explicit_null_language_resets_to_follow_the_browser(
    client: AsyncClient, user: CurrentUser
):
    await client.patch("/api/v1/me/preferences", json={"language": "en"})

    response = await client.patch("/api/v1/me/preferences", json={"language": None})

    assert response.json()["language"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{"language": "fr"}, {"stale_after_days": 0}, {"stale_after_days": 91}],
    ids=["unknown_language", "threshold_too_low", "threshold_too_high"],
)
async def test_invalid_preferences_are_rejected(
    client: AsyncClient, user: CurrentUser, payload: dict[str, object]
):
    response = await client.patch("/api/v1/me/preferences", json=payload)

    assert response.status_code == 422
