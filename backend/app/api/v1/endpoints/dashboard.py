from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_dashboard_service
from app.schemas.dashboard import DashboardRead
from app.schemas.user import CurrentUser
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", summary="Ver el dashboard")
async def get_dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardRead:
    """Métricas del usuario en una sola petición (RNF-11): recuento de solicitudes
    por estado (RF-60), envíos por semana en las últimas 12 semanas (RF-61), tasa
    de respuesta (RF-62, `null` con menos de 5 solicitudes enviadas por RF-66),
    próximas entrevistas y recordatorios pendientes o vencidos (RF-63), y
    solicitudes sin actividad (RF-64). Cada lista trae un vistazo (5 elementos) y
    su total; el listado completo de recordatorios vive en `GET /reminders`.
    """
    return await service.get(current_user.id)
