from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_current_user, get_limit_service, get_user_service
from app.domain.limits import WARNING_RATIO
from app.schemas.usage import LimitUsageRead, UsageRead
from app.schemas.user import CurrentUser, MeRead, PreferencesRead, PreferencesUpdate
from app.services.limit_service import LimitService
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


@router.get("/usage", summary="Consumo de los límites de la cuenta")
async def read_usage(
    current_user: CurrentUser = Depends(get_current_user),
    limits: LimitService = Depends(get_limit_service),
) -> UsageRead:
    """Para cada límite de la cuenta (RF-140, RF-141): cuánto lleva, su límite y
    cuánto le queda. Al alcanzar uno, la creación responde **409** con el código
    del límite y los mismos números: `{"detail", "code", "limit", "used"}`.

    | `key` | Qué cuenta | Código al alcanzarlo |
    |---|---|---|
    | `applications` | Solicitudes, archivadas incluidas | `applications_limit_reached` |
    | `companies` | Empresas | `companies_limit_reached` |
    | `reminders` | Recordatorios en cualquier estado | `reminders_limit_reached` |
    """
    usage = await limits.usage(current_user.id)
    return UsageRead(
        limits=[LimitUsageRead.model_validate(item) for item in usage],
        warning_ratio=WARNING_RATIO,
    )
