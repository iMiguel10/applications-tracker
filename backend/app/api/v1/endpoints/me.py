from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.v1.deps import (
    enforce_export_rate_limit,
    enforce_password_change_rate_limit,
    get_account_export_service,
    get_account_service,
    get_current_user,
    get_limit_service,
    get_password_service,
    get_session_handle,
    get_user_service,
)
from app.domain.account_export import export_filename
from app.domain.limits import WARNING_RATIO
from app.schemas.common import error_responses
from app.schemas.usage import LimitUsageRead, UsageRead
from app.schemas.user import (
    CurrentUser,
    MeRead,
    PasswordChange,
    PreferencesRead,
    PreferencesUpdate,
)
from app.services.account_export_service import AccountExportService
from app.services.account_service import AccountService
from app.services.limit_service import LimitService
from app.services.password_service import PasswordService
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
    accounts: AccountService = Depends(get_account_service),
) -> None:
    """Borra de forma irreversible la cuenta y todos sus datos (RNF-40, RNF-41):
    empresas, solicitudes con su historial, entrevistas, recordatorios, documentos
    con sus PDF y preferencias, y después la identidad en SuperTokens
    (credenciales y sesiones).

    Un access token ya emitido sigue validándose sin consultar al core hasta que
    caduca (máximo 5 minutos): el cliente debe cerrar sesión justo después."""
    await accounts.delete_account(current_user)


@router.get(
    "/export",
    summary="Descarga todos los datos de la cuenta",
    dependencies=[Depends(enforce_export_rate_limit)],
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "`.zip` con todos los datos de la cuenta.",
            "content": {
                "application/zip": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def export_me(
    current_user: CurrentUser = Depends(get_current_user),
    exports: AccountExportService = Depends(get_account_export_service),
) -> StreamingResponse:
    """Todos los datos de la cuenta en un `.zip` (RGPD arts. 15 y 20): un JSON por
    tipo de dato (solicitudes con su historial, empresas, entrevistas,
    recordatorios, documentos, perfil, propuestas de IA, preferencias…), los PDF en
    `documents/` y un `README.txt` que explica cada fichero.

    Nunca incluye las claves de IA, ni cifradas: solo qué proveedor y modelo. El
    fichero se genera mientras se descarga; si se corta, se vuelve a pedir.

    - **429** `rate_limited`: más de 5 exportaciones en una hora."""
    snapshot = await exports.snapshot(current_user)
    filename = export_filename(snapshot.exported_at)
    return StreamingResponse(
        exports.zip_stream(snapshot),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambia la contraseña con la actual",
    dependencies=[Depends(enforce_password_change_rate_limit)],
    responses=error_responses(400, 422),
)
async def change_password(
    data: PasswordChange,
    current_user: CurrentUser = Depends(get_current_user),
    session_handle: str = Depends(get_session_handle),
    passwords: PasswordService = Depends(get_password_service),
) -> None:
    """Cambia la contraseña de la cuenta pidiendo la actual: funciona también en
    una instalación sin correo, donde no hay enlace de recuperación.

    - **400** `wrong_current_password`: la actual no es correcta; no cambia nada.
    - **422** `password_policy`: la nueva no cumple la política de contraseñas.
    - **429** `rate_limited`: más de 5 intentos en 15 minutos.

    Al cambiarla se cierran **las demás sesiones** de la cuenta (sus refresh tokens
    dejan de servir); la de esta petición sigue abierta. Si la instalación envía
    correo, llega un aviso a la dirección de la cuenta."""
    await passwords.change(
        current_user,
        session_handle=session_handle,
        current_password=data.current_password.get_secret_value(),
        new_password=data.new_password.get_secret_value(),
    )


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
    | `documents` | Documentos, archivados incluidos | `documents_limit_reached` |
    | `storage_bytes` | Bytes de los documentos (`unit: "bytes"`) | `storage_limit_reached` |
    | `ai_cv_proposals` | Usos gratuitos de IA para el CV | `ai_free_quota_exhausted` |
    | `ai_cover_letter_proposals` | Usos gratuitos de IA para la carta | `ai_free_quota_exhausted` |

    Los usos gratuitos de IA solo aparecen si la instalación los ofrece (tiene IA
    de la plataforma). `limit` y `remaining` a `null`: sin límite.
    """
    usage = await limits.usage(current_user.id, offered_only=True)
    return UsageRead(
        limits=[LimitUsageRead.model_validate(item) for item in usage],
        warning_ratio=WARNING_RATIO,
    )
