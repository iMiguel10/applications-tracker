"""`DemoAccountService` sin el core: la cuenta de demostración vuelve a nacer
limpia cada vez, con sus límites y sin nada de lo que hubo antes."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.demo import DEMO_LIMITS
from app.domain.limits import LimitKey
from app.domain.user import Language
from app.infra.storage import LocalFileStorage
from app.repositories.identity_repository import IdentityRepository
from app.repositories.user_repository import UserRepository
from app.services.demo_account_service import DemoAccountService
from app.services.limit_service import LimitService
from tests.factories import make_application

EMAIL = "demo@example.com"


class FakeIdentities(IdentityRepository):
    def __init__(self) -> None:
        self.accounts: dict[str, str] = {}
        self.passwords: dict[str, str] = {}
        self.verified: set[str] = set()
        self.created = 0

    async def find_id_by_email(self, email: str) -> str | None:
        return self.accounts.get(email)

    async def create_account(self, email: str, password: str) -> str | None:
        if email in self.accounts:
            return None
        self.created += 1
        self.accounts[email] = f"st-{self.created}"
        self.passwords[email] = password
        return self.accounts[email]

    async def mark_email_verified(self, supertokens_user_id: str, email: str) -> None:
        self.verified.add(supertokens_user_id)

    async def delete(self, supertokens_user_id: str) -> None:
        self.accounts = {
            e: s for e, s in self.accounts.items() if s != supertokens_user_id
        }


def _service(
    session: AsyncSession, tmp_path: Path, identities: FakeIdentities
) -> DemoAccountService:
    return DemoAccountService(session, LocalFileStorage(str(tmp_path)), identities)


@pytest.mark.asyncio
async def test_first_run_creates_the_account_with_its_limits(
    db_session: AsyncSession, tmp_path: Path
):
    identities = FakeIdentities()

    await _service(db_session, tmp_path, identities).reset(
        EMAIL, "clave-demo", Language.EN
    )

    sid = identities.accounts[EMAIL]
    assert identities.passwords[EMAIL] == "clave-demo"
    assert sid in identities.verified
    user = await UserRepository(db_session).get_by_supertokens_id(sid)
    assert user is not None
    assert user.language == "en"
    assert not user.notify_reminder_due and not user.notify_interview
    usage = {item.key: item for item in await LimitService(db_session).usage(user.id)}
    for key, value in DEMO_LIMITS.items():
        assert usage[key].limit == value


@pytest.mark.asyncio
async def test_reset_removes_what_visitors_created(
    db_session: AsyncSession, tmp_path: Path
):
    identities = FakeIdentities()
    service = _service(db_session, tmp_path, identities)
    await service.reset(EMAIL, "clave-demo", Language.ES)
    old = await UserRepository(db_session).get_by_supertokens_id(
        identities.accounts[EMAIL]
    )
    assert old is not None
    await make_application(db_session, old.id)

    # Un visitante cambió la contraseña y creó una solicitud.
    identities.passwords[EMAIL] = "la-cambio-yo"
    await service.reset(EMAIL, "clave-demo", Language.ES)

    users = UserRepository(db_session)
    assert await users.get_by_id(old.id) is None
    new = await users.get_by_supertokens_id(identities.accounts[EMAIL])
    assert new is not None and new.id != old.id
    assert identities.passwords[EMAIL] == "clave-demo"
    usage = await LimitService(db_session).usage(new.id)
    applications = next(i for i in usage if i.key == LimitKey.APPLICATIONS)
    assert applications.used == 0


@pytest.mark.asyncio
async def test_an_identity_without_user_row_is_replaced(
    db_session: AsyncSession, tmp_path: Path
):
    identities = FakeIdentities()
    await identities.create_account(EMAIL, "otra")

    await _service(db_session, tmp_path, identities).reset(
        EMAIL, "clave-demo", Language.ES
    )

    assert identities.passwords[EMAIL] == "clave-demo"
