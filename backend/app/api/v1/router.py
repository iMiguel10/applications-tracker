from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user
from app.api.v1.endpoints import applications, companies, health, me
from app.schemas.auth import UnauthorizedError

router = APIRouter()

# Públicas.
router.include_router(health.router)

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

router.include_router(protected)
