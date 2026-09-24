from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_current_user, get_user_service
from app.schemas.user import CurrentUser, MeRead, PreferencesRead, PreferencesUpdate
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


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina la cuenta del usuario actual",
)
async def delete_me(
    current_user: CurrentUser = Depends(get_current_user),
    users: UserService = Depends(get_user_service),
) -> None:
    """Borra de forma irreversible la cuenta y todos sus datos (RNF-40): empresas,
    solicitudes con su historial, entrevistas, recordatorios y preferencias, y
    después la identidad en SuperTokens (credenciales y sesiones).

    Un access token ya emitido sigue validándose sin consultar al core hasta que
    caduca (máximo 5 minutos): el cliente debe cerrar sesión justo después."""
    await users.delete_account(current_user)


@router.get("/preferences", summary="Preferencias del usuario actual")
async def read_preferences(
    current_user: CurrentUser = Depends(get_current_user),
    users: UserService = Depends(get_user_service),
) -> PreferencesRead:
    """Idioma de la interfaz (F8) y umbral de "sin actividad" del dashboard
    (RF-64). `language` es `null` mientras el usuario no elige uno explícito: la
    interfaz sigue el idioma del navegador."""
    return await users.get_preferences(current_user.id)


@router.patch("/preferences", summary="Actualiza las preferencias del usuario actual")
async def update_preferences(
    data: PreferencesUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    users: UserService = Depends(get_user_service),
) -> PreferencesRead:
    """Actualización parcial: solo se cambian los campos enviados. Enviar
    `"language": null` vuelve a seguir el idioma del navegador."""
    return await users.update_preferences(current_user.id, data)
