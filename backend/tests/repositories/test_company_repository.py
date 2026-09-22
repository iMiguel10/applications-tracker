from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.company_repository import CompanyRepository
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company


@pytest.mark.asyncio
async def test_list_counts_applications_per_company_including_archived(
    db_session: AsyncSession, user: CurrentUser
):
    acme = await make_company(db_session, user.id, "Acme")
    await make_company(db_session, user.id, "Empty")
    await make_application(db_session, user.id, acme)
    await make_application(db_session, user.id, acme, archived_at=datetime.now(UTC))

    items, total = await CompanyRepository(db_session).list(
        user.id, search=None, page=1, limit=10, sort_by="name", descending=False
    )

    assert total == 2
    assert {(i.company.name, i.applications_count) for i in items} == {
        ("Acme", 2),
        ("Empty", 0),
    }


@pytest.mark.asyncio
async def test_list_does_not_count_other_users_applications(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await make_company(db_session, user.id, "Acme")
    await make_application(db_session, other_user.id)

    items, total = await CompanyRepository(db_session).list(
        user.id, search=None, page=1, limit=10, sort_by="name", descending=False
    )

    assert total == 1
    assert items[0].applications_count == 0


@pytest.mark.asyncio
async def test_search_by_name_escapes_wildcards(
    db_session: AsyncSession, user: CurrentUser
):
    await make_company(db_session, user.id, "A_B Consulting")
    await make_company(db_session, user.id, "AXB Consulting")

    items, total = await CompanyRepository(db_session).list(
        user.id, search="a_b", page=1, limit=10, sort_by="name", descending=False
    )

    assert total == 1
    assert items[0].company.name == "A_B Consulting"


@pytest.mark.asyncio
async def test_get_by_name_ignores_case(db_session: AsyncSession, user: CurrentUser):
    acme = await make_company(db_session, user.id, "Acme")

    found = await CompanyRepository(db_session).get_by_name(user.id, "aCME")

    assert found is not None
    assert found.id == acme.id
