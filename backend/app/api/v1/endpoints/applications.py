import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_application_service, get_current_user
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListQuery,
    ApplicationRead,
    ApplicationUpdate,
)
from app.schemas.common import error_responses
from app.schemas.pagination import Page
from app.schemas.user import CurrentUser
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("", summary="Listar solicitudes")
async def list_applications(
    query: Annotated[ApplicationListQuery, Query()],
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> Page[ApplicationRead]:
    """Solicitudes del usuario, paginadas y filtrables (RF-22).

    Por defecto solo las activas (no archivadas), ordenadas por fecha de envío
    descendente; las guardadas sin fecha de envío van al final.
    """
    items, total = await service.list(current_user.id, query)
    return Page[ApplicationRead].build(
        [ApplicationRead.model_validate(item) for item in items],
        total=total,
        page=query.page,
        limit=query.limit,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear una solicitud",
    responses=error_responses(404, 409),
)
async def create_application(
    data: ApplicationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationRead:
    """Registra una solicitud en estado `saved` o `applied` (RF-20).

    La empresa debe existir y ser del usuario (404 si no). 409
    `applications_limit_reached` al superar 5 000 solicitudes.
    """
    return ApplicationRead.model_validate(await service.create(current_user.id, data))


@router.get(
    "/{application_id}",
    summary="Ver una solicitud",
    responses=error_responses(404),
)
async def get_application(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationRead:
    """Detalle de una solicitud del usuario."""
    return ApplicationRead.model_validate(
        await service.get(current_user.id, application_id)
    )


@router.patch(
    "/{application_id}",
    summary="Editar una solicitud",
    responses=error_responses(404, 422),
)
async def update_application(
    application_id: uuid.UUID,
    data: ApplicationUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationRead:
    """Actualización parcial de los datos (RF-21): solo cambian los campos enviados y
    `null` vacía un campo opcional. El estado no se cambia aquí.

    422 `salary_range_invalid` o `applied_at_required` si el resultado incumple
    las reglas teniendo en cuenta también los valores ya guardados.
    """
    return ApplicationRead.model_validate(
        await service.update(current_user.id, application_id, data)
    )


@router.post(
    "/{application_id}/archive",
    summary="Archivar una solicitud",
    responses=error_responses(404),
)
async def archive_application(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationRead:
    """Oculta la solicitud del listado por defecto sin borrarla; sigue contando en
    las métricas (RF-24). Idempotente."""
    return ApplicationRead.model_validate(
        await service.archive(current_user.id, application_id)
    )


@router.post(
    "/{application_id}/unarchive",
    summary="Desarchivar una solicitud",
    responses=error_responses(404),
)
async def unarchive_application(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationRead:
    """Devuelve la solicitud al listado de activas. Idempotente."""
    return ApplicationRead.model_validate(
        await service.unarchive(current_user.id, application_id)
    )


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar una solicitud",
    responses=error_responses(404),
)
async def delete_application(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
) -> None:
    """Borra la solicitud definitivamente (RF-25). Para ocultarla sin perderla,
    usar archivar."""
    await service.delete(current_user.id, application_id)
