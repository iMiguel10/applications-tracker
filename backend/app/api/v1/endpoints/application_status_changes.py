import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_application_status_service, get_current_user
from app.schemas.application import ApplicationRead
from app.schemas.application_status_change import (
    ApplicationStatusChangeCreate,
    ApplicationStatusChangeRead,
)
from app.schemas.common import error_responses
from app.schemas.user import CurrentUser
from app.services.application_status_service import ApplicationStatusService

router = APIRouter(
    prefix="/applications/{application_id}/status-changes", tags=["Applications"]
)


@router.get(
    "",
    summary="Ver el historial de estados",
    responses=error_responses(404),
)
async def list_status_changes(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStatusService = Depends(get_application_status_service),
) -> list[ApplicationStatusChangeRead]:
    """Historial completo de la solicitud (RF-23), del cambio más reciente al más
    antiguo (orden por `seq`, no por fecha: ver `changed_at` frente a `created_at`
    en la arquitectura)."""
    changes = await service.list_history(current_user.id, application_id)
    return [ApplicationStatusChangeRead.model_validate(change) for change in changes]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Cambiar el estado de una solicitud",
    responses=error_responses(404, 409, 422),
)
async def change_status(
    application_id: uuid.UUID,
    data: ApplicationStatusChangeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStatusService = Depends(get_application_status_service),
) -> ApplicationRead:
    """Registra una transición del ciclo de vida (RF-30…33).

    Solo se permiten las transiciones de la especificación §6; cualquier otra
    responde 409 `invalid_transition`. Si la nueva situación es `applied` y la
    solicitud no tenía fecha de envío, se fija a la de `changed_at`. 422
    `changed_at_in_future` o `changed_at_before_last_change` si la fecha no encaja
    entre el último cambio y ahora.
    """
    return ApplicationRead.model_validate(
        await service.change(current_user.id, application_id, data)
    )


@router.delete(
    "/last",
    summary="Deshacer el último cambio de estado",
    responses=error_responses(404, 409),
)
async def undo_last_status_change(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationStatusService = Depends(get_application_status_service),
) -> ApplicationRead:
    """Elimina el último cambio del historial y restaura el estado anterior (RF-34),
    para corregir un error sin dejar rastro. 409 `cannot_undo_initial_change` si el
    único cambio que queda es el que creó la solicitud."""
    return ApplicationRead.model_validate(
        await service.undo_last(current_user.id, application_id)
    )
