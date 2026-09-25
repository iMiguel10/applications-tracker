from fastapi import APIRouter, Depends

from app.api.v1.deps import enforce_api_rate_limit, get_current_user
from app.api.v1.endpoints import (
    application_status_changes,
    applications,
    companies,
    dashboard,
    health,
    interviews,
    me,
    meta,
    reminders,
)
from app.schemas.auth import UnauthorizedError
from app.schemas.common import RateLimitedRead

router = APIRouter()

# Lo único que responde sin sesión. La prueba T1 (test_auth_protection.py) guarda
# la misma lista: un endpoint público nuevo exige tocarla, y por tanto revisarlo.
public = APIRouter()
public.include_router(health.router)
public.include_router(meta.router)

router.include_router(public)

# Todo lo que se incluye aquí exige sesión (invariante 8). Un endpoint nuevo queda
# protegido por construcción, sin depender de acordarse de añadir la dependencia.
protected = APIRouter(
    # La sesión primero; el límite general por usuario, después (RNF-04).
    dependencies=[Depends(get_current_user), Depends(enforce_api_rate_limit)],
    responses={
        401: {
            "model": UnauthorizedError,
            "description": "Sin sesión, o el access token ha caducado o no es válido.",
        },
        429: {
            "model": RateLimitedRead,
            "description": "Demasiadas peticiones de este usuario (600 por minuto). "
            "`Retry-After` dice cuántos segundos esperar.",
        },
    },
)
protected.include_router(me.router)
protected.include_router(companies.router)
protected.include_router(applications.router)
protected.include_router(application_status_changes.router)
protected.include_router(interviews.router)
protected.include_router(reminders.router)
protected.include_router(dashboard.router)

router.include_router(protected)
