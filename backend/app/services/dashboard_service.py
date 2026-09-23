import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.application_status import ApplicationStatus
from app.domain.dashboard import (
    MIN_SAMPLE_FOR_RATE,
    RESPONSE_REACHED_STATUSES,
    STALE_AFTER_DAYS,
    WAITING_STATUSES,
    WEEKS_OF_HISTORY,
    WIDGET_LIST_LIMIT,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.reminder_repository import ReminderFilters, ReminderRepository
from app.schemas.company import CompanySummary
from app.schemas.dashboard import (
    ApplicationSummary,
    DashboardRead,
    ResponseRate,
    StaleApplication,
    StatusCount,
    UpcomingInterview,
    WeeklyApplications,
)
from app.schemas.reminder import ReminderRead


class DashboardService:
    """Agrega RF-60…64 en una sola respuesta (RNF-11): varias consultas ligeras y
    ya indexadas, no una foto materializada. Solo lee: no es dueño de ninguna
    transacción de escritura."""

    def __init__(self, session: AsyncSession) -> None:
        self.applications = ApplicationRepository(session)
        self.interviews = InterviewRepository(session)
        self.reminders = ReminderRepository(session)

    async def get(self, user_id: uuid.UUID) -> DashboardRead:
        now = datetime.now(UTC)

        status_counts = await self._status_counts(user_id)
        weekly = await self._applications_per_week(user_id, now)
        response_rate = await self._response_rate(user_id)

        interview_rows = await self.interviews.list_upcoming(
            user_id, after=now, limit=WIDGET_LIST_LIMIT
        )
        upcoming_interviews_total = await self.interviews.count_upcoming(
            user_id, after=now
        )
        upcoming_interviews = [
            UpcomingInterview(
                id=interview.id,
                scheduled_at=interview.scheduled_at,
                interview_type=interview.interview_type,
                format=interview.format,
                # No contains_eager aquí (la fila viene de tres selects, no de una
                # relación): se construye a mano en vez de arriesgar el lazy="raise".
                application=ApplicationSummary(
                    id=application.id,
                    position_title=application.position_title,
                    company=CompanySummary.model_validate(company),
                    status=ApplicationStatus(application.status),
                ),
            )
            for interview, application, company in interview_rows
        ]

        pending_reminders, pending_reminders_total = await self.reminders.list(
            user_id,
            ReminderFilters(statuses=["pending"]),
            page=1,
            limit=WIDGET_LIST_LIMIT,
            sort_by="due_at",
            descending=False,
        )

        stale_before = now - timedelta(days=STALE_AFTER_DAYS)
        stale_rows, stale_total = await self.applications.list_stale(
            user_id,
            statuses=[status.value for status in WAITING_STATUSES],
            before=stale_before,
            limit=WIDGET_LIST_LIMIT,
        )
        stale_applications = [
            StaleApplication(
                application=ApplicationSummary.model_validate(application),
                last_activity_at=application.last_activity_at,
                days_since_activity=(now - application.last_activity_at).days,
            )
            for application in stale_rows
        ]

        return DashboardRead(
            status_counts=status_counts,
            applications_per_week=weekly,
            response_rate=response_rate,
            upcoming_interviews=upcoming_interviews,
            upcoming_interviews_total=upcoming_interviews_total,
            pending_reminders=[
                ReminderRead.model_validate(reminder) for reminder in pending_reminders
            ],
            pending_reminders_total=pending_reminders_total,
            stale_applications=stale_applications,
            stale_applications_total=stale_total,
            stale_after_days=STALE_AFTER_DAYS,
        )

    async def _status_counts(self, user_id: uuid.UUID) -> list[StatusCount]:
        rows = await self.applications.count_by_status(user_id)
        counts = {status: count for status, count in rows}
        # Todos los estados aparecen, incluso en cero: el frontend dibuja un hueco
        # completo, no uno que va apareciendo columna a columna.
        return [
            StatusCount(status=status, count=counts.get(status.value, 0))
            for status in ApplicationStatus
        ]

    async def _applications_per_week(
        self, user_id: uuid.UUID, now: datetime
    ) -> list[WeeklyApplications]:
        this_monday = now.date() - timedelta(days=now.weekday())
        since = this_monday - timedelta(weeks=WEEKS_OF_HISTORY - 1)

        rows = await self.applications.applications_per_week(user_id, since=since)
        counts = {week_start.date(): count for week_start, count in rows}

        return [
            WeeklyApplications(
                week_start=week,
                count=counts.get(week, 0),
            )
            for week in (
                since + timedelta(weeks=offset) for offset in range(WEEKS_OF_HISTORY)
            )
        ]

    async def _response_rate(self, user_id: uuid.UUID) -> ResponseRate:
        sent_count, reached_count = await self.applications.response_rate_counts(
            user_id,
            reached_statuses=[status.value for status in RESPONSE_REACHED_STATUSES],
        )
        rate = reached_count / sent_count if sent_count >= MIN_SAMPLE_FOR_RATE else None
        return ResponseRate(
            sent_count=sent_count, reached_count=reached_count, rate=rate
        )
