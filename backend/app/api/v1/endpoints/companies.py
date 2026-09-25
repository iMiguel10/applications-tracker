import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import get_company_service, get_current_user
from app.repositories.company_repository import CompanyWithCount
from app.schemas.common import error_responses
from app.schemas.company import (
    CompanyCreate,
    CompanyListQuery,
    CompanyRead,
    CompanyUpdate,
)
from app.schemas.pagination import Page
from app.schemas.user import CurrentUser
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies"])


def _read(item: CompanyWithCount) -> CompanyRead:
    company = item.company
    return CompanyRead(
        id=company.id,
        name=company.name,
        website=company.website,
        location=company.location,
        notes=company.notes,
        applications_count=item.applications_count,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


@router.get("", summary="Listar empresas")
async def list_companies(
    query: Annotated[CompanyListQuery, Query()],
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> Page[CompanyRead]:
    """Empresas del usuario, con el número de solicitudes de cada una (RF-11)."""
    items, total = await service.list(current_user.id, query)
    return Page[CompanyRead].build(
        [_read(item) for item in items], total=total, page=query.page, limit=query.limit
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear una empresa",
    responses=error_responses(409),
)
async def create_company(
    data: CompanyCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> CompanyRead:
    """Crea una empresa. El nombre es único por usuario sin distinguir mayúsculas:
    si ya existe, responde 409 `company_name_taken`. 409
    `companies_limit_reached` al alcanzar el límite de empresas de la cuenta (2 000
    por defecto), con `limit` y `used`; el consumo, en `GET /me/usage`."""
    return _read(await service.create(current_user.id, data))


@router.get("/{company_id}", summary="Ver una empresa", responses=error_responses(404))
async def get_company(
    company_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> CompanyRead:
    """Detalle de una empresa del usuario."""
    return _read(await service.get(current_user.id, company_id))


@router.patch(
    "/{company_id}",
    summary="Editar una empresa",
    responses=error_responses(404, 409),
)
async def update_company(
    company_id: uuid.UUID,
    data: CompanyUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> CompanyRead:
    """Actualización parcial: solo cambian los campos enviados; `null` vacía un campo
    opcional. 409 `company_name_taken` si el nombre nuevo ya existe."""
    return _read(await service.update(current_user.id, company_id, data))


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar una empresa",
    responses=error_responses(404, 409),
)
async def delete_company(
    company_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
) -> None:
    """Borra una empresa sin solicitudes. Si tiene alguna (incluidas archivadas),
    responde 409 `company_in_use` (RF-12)."""
    await service.delete(current_user.id, company_id)
