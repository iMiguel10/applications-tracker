from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.application_repository import (
    ApplicationFilters,
    ApplicationRepository,
    ApplicationSort,
)
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company, make_status_change


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


# --- Dashboard (F5) y exportación ------------------------------------------------


@pytest.mark.asyncio
async def test_count_by_status_excludes_archived(
    db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id, status="applied")
    await make_application(db_session, user.id, status="applied")
    await make_application(db_session, user.id, status="saved", applied_at=None)
    await make_application(
        db_session,
        user.id,
        status="applied",
        archived_at=datetime.now(UTC),
    )

    rows = await ApplicationRepository(db_session).count_by_status(user.id)

    assert {status: count for status, count in rows} == {"applied": 2, "saved": 1}


@pytest.mark.asyncio
async def test_applications_per_week_groups_by_iso_week_and_includes_archived(
    db_session: AsyncSession, user: CurrentUser
):
    # Semana ISO del 2026-09-07 (lunes) al 2026-09-13 (domingo).
    await make_application(db_session, user.id, applied_at=date(2026, 9, 7))
    await make_application(
        db_session,
        user.id,
        applied_at=date(2026, 9, 13),
        archived_at=datetime.now(UTC),
    )
    # Semana siguiente: no debe mezclarse con la anterior.
    await make_application(db_session, user.id, applied_at=date(2026, 9, 14))

    rows = await ApplicationRepository(db_session).applications_per_week(
        user.id, since=date(2026, 9, 7)
    )

    assert {(week.date(), count) for week, count in rows} == {
        (date(2026, 9, 7), 2),
        (date(2026, 9, 14), 1),
    }


@pytest.mark.asyncio
async def test_response_rate_counts_only_sent_applications_that_reached_screening(
    db_session: AsyncSession, user: CurrentUser
):
    reached = await make_application(db_session, user.id, status="applied")
    await make_status_change(db_session, reached, to_status="screening")
    # Llegó a screening y luego la rechazaron: sigue contando como "alcanzada".
    await make_status_change(db_session, reached, to_status="rejected")

    await make_application(db_session, user.id, status="applied")  # nunca respondió
    await make_application(db_session, user.id, status="saved", applied_at=None)

    sent, reached_count = await ApplicationRepository(db_session).response_rate_counts(
        user.id, reached_statuses=["screening", "interviewing", "offer", "accepted"]
    )

    assert (sent, reached_count) == (2, 1)


@pytest.mark.asyncio
async def test_list_stale_only_active_waiting_applications_past_the_cutoff(
    db_session: AsyncSession, user: CurrentUser
):
    now = datetime.now(UTC)
    stale = await make_application(
        db_session,
        user.id,
        position_title="Stale",
        status="applied",
        last_activity_at=now - timedelta(days=20),
    )
    await make_application(
        db_session,
        user.id,
        position_title="Recent",
        status="applied",
        last_activity_at=now - timedelta(days=1),
    )
    await make_application(
        db_session,
        user.id,
        position_title="Saved, not waiting",
        status="saved",
        applied_at=None,
        last_activity_at=now - timedelta(days=20),
    )
    await make_application(
        db_session,
        user.id,
        position_title="Archived",
        status="applied",
        last_activity_at=now - timedelta(days=20),
        archived_at=now,
    )

    items, total = await ApplicationRepository(db_session).list_stale(
        user.id,
        statuses=["applied", "screening", "interviewing", "offer"],
        before=now - timedelta(days=14),
        limit=10,
    )

    assert total == 1
    assert [item.id for item in items] == [stale.id]


@pytest.mark.asyncio
async def test_list_all_includes_archived_and_only_the_users_own(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await make_application(db_session, user.id, position_title="Activa")
    await make_application(
        db_session,
        user.id,
        position_title="Archivada",
        archived_at=datetime.now(UTC),
    )
    await make_application(db_session, other_user.id, position_title="Ajena")

    items = await ApplicationRepository(db_session).list_all(user.id)

    assert {item.position_title for item in items} == {"Activa", "Archivada"}
