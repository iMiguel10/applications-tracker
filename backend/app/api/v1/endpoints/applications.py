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
    """Registra una solicitud nueva.

    Versión F0 (provisional): solo puesto y empresa en texto. En F2 se amplía con
    empresa registrada, estado, fechas y el resto de datos.
    """
    application = await service.create(data)
    return ApplicationRead.model_validate(application)


@router.get(
    "",
    summary="Listar solicitudes",
)
async def list_applications(
    page: int = Query(default=1, ge=1, description="Página, empezando en 1."),
    limit: int = Query(
        default=20, ge=1, le=100, description="Elementos por página (máximo 100)."
    ),
    service: ApplicationService = Depends(get_application_service),
) -> Page[ApplicationRead]:
    """Lista paginada de solicitudes, las más recientes primero.

    Versión F0 (provisional): todavía no se filtra por usuario; en F2 cada usuario
    verá solo las suyas.
    """
    items, total = await service.list(page=page, limit=limit)
    return Page[ApplicationRead].build(
        [ApplicationRead.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
    )
