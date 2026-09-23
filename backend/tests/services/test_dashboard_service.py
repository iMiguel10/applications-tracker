from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.application_status import ApplicationStatus
from app.domain.dashboard import STALE_AFTER_DAYS, WIDGET_LIST_LIMIT
from app.schemas.user import CurrentUser
from app.services.dashboard_service import DashboardService
from tests.factories import (
    make_application,
    make_interview,
    make_reminder,
    make_status_change,
)


@pytest.mark.asyncio
async def test_status_counts_include_every_status_even_at_zero(
    db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id, status="applied")

    dashboard = await DashboardService(db_session).get(user.id)

    counts = {row.status: row.count for row in dashboard.status_counts}
    assert set(counts) == set(ApplicationStatus)
    assert counts[ApplicationStatus.APPLIED] == 1
    assert counts[ApplicationStatus.SAVED] == 0


@pytest.mark.asyncio
async def test_applications_per_week_always_covers_twelve_weeks(
    db_session: AsyncSession, user: CurrentUser
):
    dashboard = await DashboardService(db_session).get(user.id)

    assert len(dashboard.applications_per_week) == 12
    assert all(week.count == 0 for week in dashboard.applications_per_week)
    # Semanas consecutivas, sin huecos.
    starts = [week.week_start for week in dashboard.applications_per_week]
    assert starts == sorted(starts)
    assert (starts[-1] - starts[0]).days == 11 * 7


@pytest.mark.asyncio
async def test_response_rate_is_null_below_the_minimum_sample(
    db_session: AsyncSession, user: CurrentUser
):
    for _ in range(4):
        await make_application(db_session, user.id, status="applied")

    dashboard = await DashboardService(db_session).get(user.id)

    assert dashboard.response_rate.sent_count == 4
    assert dashboard.response_rate.rate is None


@pytest.mark.asyncio
async def test_response_rate_is_computed_at_the_minimum_sample(
    db_session: AsyncSession, user: CurrentUser
):
    for _ in range(4):
        await make_application(db_session, user.id, status="applied")
    reached = await make_application(db_session, user.id, status="applied")
    await make_status_change(db_session, reached, to_status="screening")

    dashboard = await DashboardService(db_session).get(user.id)

    assert dashboard.response_rate.sent_count == 5
    assert dashboard.response_rate.reached_count == 1
    assert dashboard.response_rate.rate == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_upcoming_interviews_widget_is_capped_with_a_total(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    now = datetime.now(UTC)
    for day in range(WIDGET_LIST_LIMIT + 2):
        await make_interview(
            db_session, application, scheduled_at=now + timedelta(days=day + 1)
        )

    dashboard = await DashboardService(db_session).get(user.id)

    assert len(dashboard.upcoming_interviews) == WIDGET_LIST_LIMIT
    assert dashboard.upcoming_interviews_total == WIDGET_LIST_LIMIT + 2
    assert dashboard.upcoming_interviews[0].application.id == application.id


@pytest.mark.asyncio
async def test_pending_reminders_widget_is_capped_with_a_total(
    db_session: AsyncSession, user: CurrentUser
):
    for _ in range(WIDGET_LIST_LIMIT + 1):
        await make_reminder(db_session, user.id)
    await make_reminder(db_session, user.id, status="done")

    dashboard = await DashboardService(db_session).get(user.id)

    assert len(dashboard.pending_reminders) == WIDGET_LIST_LIMIT
    assert dashboard.pending_reminders_total == WIDGET_LIST_LIMIT + 1


@pytest.mark.asyncio
async def test_stale_applications_widget_reports_days_since_activity(
    db_session: AsyncSession, user: CurrentUser
):
    now = datetime.now(UTC)
    stale = await make_application(
        db_session,
        user.id,
        status="applied",
        last_activity_at=now - timedelta(days=STALE_AFTER_DAYS + 5),
    )
    await make_application(db_session, user.id, status="applied", last_activity_at=now)

    dashboard = await DashboardService(db_session).get(user.id)

    assert dashboard.stale_after_days == STALE_AFTER_DAYS
    assert dashboard.stale_applications_total == 1
    assert dashboard.stale_applications[0].application.id == stale.id
    assert dashboard.stale_applications[0].days_since_activity >= STALE_AFTER_DAYS + 5


@pytest.mark.asyncio
async def test_dashboard_only_reflects_the_current_users_data(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await make_application(db_session, other_user.id, status="applied")

    dashboard = await DashboardService(db_session).get(user.id)

    counts = {row.status: row.count for row in dashboard.status_counts}
    assert counts[ApplicationStatus.APPLIED] == 0
