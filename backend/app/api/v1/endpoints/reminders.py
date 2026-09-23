import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_current_user, get_reminder_service
from app.schemas.common import error_responses
from app.schemas.pagination import Page
from app.schemas.reminder import ReminderCreate, ReminderListQuery, ReminderRead
from app.schemas.user import CurrentUser
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("", summary="Listar recordatorios")
async def list_reminders(
    query: Annotated[ReminderListQuery, Query()],
    current_user: CurrentUser = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
) -> Page[ReminderRead]:
    """Recordatorios del usuario (RF-52), por defecto solo los pendientes. Filtra
    por `application_id` para los de una solicitud concreta (su detalle, RF-52)."""
    items, total = await service.list(current_user.id, query)
    return Page[ReminderRead].build(
        [ReminderRead.model_validate(item) for item in items],
        total=total,
        page=query.page,
        limit=query.limit,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear un recordatorio",
    responses=error_responses(404, 409),
)
async def create_reminder(
    data: ReminderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
) -> ReminderRead:
    """Crea un recordatorio, opcionalmente ligado a una solicitud (RF-50). 404 si
    `application_id` no existe o es de otro usuario. 409
    `reminders_limit_reached` al superar 500 recordatorios **pendientes**."""
    return ReminderRead.model_validate(await service.create(current_user.id, data))


@router.post(
    "/{reminder_id}/complete",
    summary="Marcar un recordatorio como hecho",
    responses=error_responses(404, 409),
)
async def complete_reminder(
    reminder_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
) -> ReminderRead:
    """RF-51. 409 `reminder_not_pending` si ya estaba hecho o descartado."""
    return ReminderRead.model_validate(
        await service.complete(current_user.id, reminder_id)
    )


@router.post(
    "/{reminder_id}/dismiss",
    summary="Descartar un recordatorio",
    responses=error_responses(404, 409),
)
async def dismiss_reminder(
    reminder_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
) -> ReminderRead:
    """RF-51. 409 `reminder_not_pending` si ya estaba hecho o descartado."""
    return ReminderRead.model_validate(
        await service.dismiss(current_user.id, reminder_id)
    )
