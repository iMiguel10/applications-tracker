import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.calendar import CalendarEventKind
from app.repositories.interview_repository import InterviewRepository
from app.repositories.reminder_repository import ReminderRepository
from app.schemas.calendar import (
    CalendarApplication,
    CalendarEvent,
    CalendarEventsQuery,
    CalendarEventsRead,
)
from app.schemas.company import CompanySummary


class CalendarService:
    """Calendario de entrevistas y recordatorios pendientes (RF-130, RF-131)."""

    def __init__(self, session: AsyncSession) -> None:
        self.interviews = InterviewRepository(session)
        self.reminders = ReminderRepository(session)

    async def events(
        self, user_id: uuid.UUID, query: CalendarEventsQuery
    ) -> CalendarEventsRead:
        interview_rows = await self.interviews.list_between(
            user_id, start=query.start, end=query.end
        )
        reminders = await self.reminders.list_pending_between(
            user_id, start=query.start, end=query.end
        )

        events = [
            CalendarEvent(
                kind=CalendarEventKind.INTERVIEW,
                id=interview.id,
                starts_at=interview.scheduled_at,
                duration_minutes=interview.duration_minutes,
                interview_type=interview.interview_type,
                format=interview.format,
                interviewers=interview.interviewers,
                outcome=interview.outcome,
                application=CalendarApplication(
                    id=application.id,
                    position_title=application.position_title,
                    company=CompanySummary(id=company.id, name=company.name),
                ),
            )
            for interview, application, company in interview_rows
        ] + [
            CalendarEvent(
                kind=CalendarEventKind.REMINDER,
                id=reminder.id,
                starts_at=reminder.due_at,
                title=reminder.title,
                application=(
                    CalendarApplication.model_validate(reminder.application)
                    if reminder.application
                    else None
                ),
            )
            for reminder in reminders
        ]
        # Cada lista ya viene ordenada; juntas, por la hora y, a la misma hora, las
        # entrevistas antes que los recordatorios.
        events.sort(
            key=lambda event: (
                event.starts_at,
                event.kind != CalendarEventKind.INTERVIEW,
            )
        )
        return CalendarEventsRead(events=events)
