from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_calendar_service, get_current_user
from app.schemas.calendar import CalendarEventsQuery, CalendarEventsRead
from app.schemas.common import error_responses
from app.schemas.user import CurrentUser
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["Calendario"])


@router.get(
    "/events",
    summary="Ver los eventos del calendario",
    responses=error_responses(422),
)
async def list_calendar_events(
    query: Annotated[CalendarEventsQuery, Query()],
    current_user: CurrentUser = Depends(get_current_user),
    service: CalendarService = Depends(get_calendar_service),
) -> CalendarEventsRead:
    """Entrevistas y recordatorios pendientes que caen en `[start, end)` (RF-130),
    ordenados por hora, cada uno con su solicitud y su empresa para enlazarlos
    (RF-131). Entran las entrevistas de cualquier resultado salvo las canceladas, y
    solo los recordatorios pendientes (también los vencidos).

    El rango va en instantes con zona (ISO 8601): la interfaz lo calcula en la zona
    horaria de la cuenta. 422 si `end` no es posterior a `start` o si el rango pasa
    de 62 días.
    """
    return await service.events(current_user.id, query)
