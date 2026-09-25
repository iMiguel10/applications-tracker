import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, LimitReachedError
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.schemas.user import CurrentUser
from app.services.company_service import CompanyService
from tests.factories import make_application, make_company


@pytest.mark.asyncio
async def test_create_rejects_existing_name_ignoring_case(
    db_session: AsyncSession, user: CurrentUser
):
    await make_company(db_session, user.id, "Acme")

    with pytest.raises(ConflictError) as error:
        await CompanyService(db_session).create(user.id, CompanyCreate(name="acme"))

    assert error.value.code == "company_name_taken"


@pytest.mark.asyncio
async def test_rename_to_same_name_with_other_case_is_allowed(
    db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id, "Acme")

    updated = await CompanyService(db_session).update(
        user.id, company.id, CompanyUpdate(name="ACME")
    )

    assert updated.company.name == "ACME"


@pytest.mark.asyncio
async def test_delete_company_with_applications_is_rejected(
    db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)
    await make_application(db_session, user.id, company)

    with pytest.raises(ConflictError) as error:
        await CompanyService(db_session).delete(user.id, company.id)

    assert error.value.code == "company_in_use"


@pytest.mark.asyncio
async def test_create_fails_when_limit_is_reached(
    db_session: AsyncSession, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "limit_companies", 1)
    await make_company(db_session, user.id)

    with pytest.raises(LimitReachedError) as error:
        await CompanyService(db_session).create(user.id, CompanyCreate(name="Otra"))

    assert error.value.code == "companies_limit_reached"
