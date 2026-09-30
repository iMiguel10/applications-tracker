from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_profile_service
from app.schemas.common import error_responses
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.schemas.user import CurrentUser
from app.services.profile_service import ProfileService

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)


@router.get("", summary="Perfil profesional del usuario actual")
async def read_profile(
    current_user: CurrentUser = Depends(get_current_user),
    profiles: ProfileService = Depends(get_profile_service),
) -> ProfileRead:
    """Datos de contacto y resumen del CV (RF-100). Un perfil que nunca se ha
    guardado se devuelve vacío, no como 404."""
    return await profiles.get(current_user.id)


@router.put(
    "",
    summary="Guarda el perfil profesional del usuario actual",
    responses=error_responses(422),
)
async def update_profile(
    data: ProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    profiles: ProfileService = Depends(get_profile_service),
) -> ProfileRead:
    """Sustituye los datos básicos enteros: un campo que no se envía queda vacío.
    Los enlaces solo admiten `http` y `https` (hasta 10)."""
    return await profiles.update(current_user.id, data)
