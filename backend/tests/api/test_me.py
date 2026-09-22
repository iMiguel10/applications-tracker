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
