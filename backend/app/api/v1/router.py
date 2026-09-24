from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user
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
    dependencies=[Depends(get_current_user)],
    responses={
        401: {
            "model": UnauthorizedError,
            "description": "Sin sesión, o el access token ha caducado o no es válido.",
        }
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
