from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.application_repository import (
    ApplicationFilters,
    ApplicationRepository,
    ApplicationSort,
)
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company


async def _titles(
    session: AsyncSession,
    user: CurrentUser,
    filters: ApplicationFilters | None = None,
    *,
    sort_by: ApplicationSort = "applied_at",
    descending: bool = True,
) -> list[str]:
    items, _ = await ApplicationRepository(session).list(
        user.id,
        filters or ApplicationFilters(),
        page=1,
        limit=100,
        sort_by=sort_by,
        descending=descending,
    )
    return [item.position_title for item in items]


@pytest.mark.asyncio
async def test_list_only_returns_own_applications(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await make_application(db_session, user.id, position_title="Mía")
    await make_application(db_session, other_user.id, position_title="Ajena")

    assert await _titles(db_session, user) == ["Mía"]


@pytest.mark.asyncio
async def test_get_does_not_return_another_users_application(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    others = await make_application(db_session, other_user.id)

    assert await ApplicationRepository(db_session).get(user.id, others.id) is None


@pytest.mark.asyncio
async def test_filters_by_status_and_work_mode(
    db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id, position_title="A", work_mode="remote")
    await make_application(
        db_session, user.id, position_title="B", status="saved", applied_at=None
    )
    await make_application(db_session, user.id, position_title="C", work_mode="onsite")

    remote_applied = ApplicationFilters(statuses=["applied"], work_modes=["remote"])

    assert await _titles(db_session, user, remote_applied) == ["A"]


@pytest.mark.asyncio
async def test_archived_filter(db_session: AsyncSession, user: CurrentUser):
    await make_application(db_session, user.id, position_title="Activa")
    await make_application(
        db_session, user.id, position_title="Archivada", archived_at=datetime.now(UTC)
    )

    assert await _titles(db_session, user) == ["Activa"]
    assert await _titles(db_session, user, ApplicationFilters(archived=True)) == [
        "Archivada"
    ]
    assert len(await _titles(db_session, user, ApplicationFilters(archived=None))) == 2


@pytest.mark.asyncio
async def test_search_matches_position_or_company_name(
    db_session: AsyncSession, user: CurrentUser
):
    globex = await make_company(db_session, user.id, "Globex")
    await make_application(db_session, user.id, position_title="Backend Developer")
    await make_application(
        db_session, user.id, globex, position_title="Frontend Developer"
    )
    await make_application(db_session, user.id, position_title="QA")

    assert sorted(
        await _titles(db_session, user, ApplicationFilters(search="back"))
    ) == ["Backend Developer"]
    assert await _titles(db_session, user, ApplicationFilters(search="GLOB")) == [
        "Frontend Developer"
    ]


@pytest.mark.asyncio
async def test_search_treats_like_wildcards_literally(
    db_session: AsyncSession, user: CurrentUser
):
    # Sin escapar, "%" encontraría todo y "_" cualquier carácter.
    await make_application(db_session, user.id, position_title="Growth 100% remote")
    await make_application(db_session, user.id, position_title="Growth 1000 onsite")
    await make_application(db_session, user.id, position_title="dev_ops")
    await make_application(db_session, user.id, position_title="dev-ops")

    assert await _titles(db_session, user, ApplicationFilters(search="100%")) == [
        "Growth 100% remote"
    ]
    assert await _titles(db_session, user, ApplicationFilters(search="dev_ops")) == [
        "dev_ops"
    ]


@pytest.mark.asyncio
async def test_applied_date_range_is_inclusive(
    db_session: AsyncSession, user: CurrentUser
):
    await make_application(
        db_session, user.id, position_title="Ago", applied_at=date(2026, 8, 31)
    )
    await make_application(
        db_session, user.id, position_title="1 Sep", applied_at=date(2026, 9, 1)
    )
    await make_application(
        db_session, user.id, position_title="10 Sep", applied_at=date(2026, 9, 10)
    )

    september = ApplicationFilters(
        applied_from=date(2026, 9, 1), applied_to=date(2026, 9, 10)
    )

    assert await _titles(db_session, user, september) == ["10 Sep", "1 Sep"]


@pytest.mark.asyncio
@pytest.mark.parametrize("descending", [True, False])
async def test_applications_without_applied_at_always_go_last(
    db_session: AsyncSession, user: CurrentUser, descending: bool
):
    await make_application(
        db_session, user.id, position_title="Guardada", status="saved", applied_at=None
    )
    await make_application(
        db_session, user.id, position_title="Vieja", applied_at=date(2026, 1, 1)
    )
    await make_application(
        db_session, user.id, position_title="Nueva", applied_at=date(2026, 9, 1)
    )

    titles = await _titles(db_session, user, descending=descending)

    assert titles[-1] == "Guardada"


@pytest.mark.asyncio
async def test_sort_by_company_name_ignores_case(
    db_session: AsyncSession, user: CurrentUser
):
    for name in ("beta", "Alpha", "Gamma"):
        company = await make_company(db_session, user.id, name)
        await make_application(db_session, user.id, company, position_title=name)

    assert await _titles(db_session, user, sort_by="company", descending=False) == [
        "Alpha",
        "beta",
        "Gamma",
    ]
