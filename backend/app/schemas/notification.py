from pydantic import BaseModel, Field

from app.domain.notifications import NotificationKind


class UnsubscribeRead(BaseModel):
    kind: NotificationKind = Field(
        description="El tipo de aviso al que se refiere el enlace: `reminder_due`, "
        "`interview_upcoming`, `weekly_digest` o `stale_application`.",
        examples=["reminder_due"],
    )
