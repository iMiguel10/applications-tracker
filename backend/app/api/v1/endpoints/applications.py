from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_application_service
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.schemas.pagination import Page
from app.services.application_service import ApplicationService

router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear una solicitud",
)
async def create_application(
    data: ApplicationCreate,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationRead:
    application = await service.create(data)
    return ApplicationRead.model_validate(application)


@router.get(
    "",
    summary="Listar solicitudes (más recientes primero)",
)
async def list_applications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    service: ApplicationService = Depends(get_application_service),
) -> Page[ApplicationRead]:
    items, total = await service.list(page=page, limit=limit)
    return Page[ApplicationRead].build(
        [ApplicationRead.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )
