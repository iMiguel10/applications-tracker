from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_user_service
from app.schemas.user import CurrentUser, MeRead
from app.services.user_service import UserService

router = APIRouter(
    prefix="/me",
    tags=["Me"],
)


@router.get("", summary="Usuario de la sesión actual")
async def read_me(
    current_user: CurrentUser = Depends(get_current_user),
    users: UserService = Depends(get_user_service),
) -> MeRead:
    """Devuelve el usuario autenticado. El email se lee de SuperTokens en cada
    llamada: esta API no guarda datos de identidad."""
    return await users.get_me(current_user)
