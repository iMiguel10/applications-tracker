from fastapi import APIRouter

from app.core.config import settings
from app.schemas.meta import MetaRead

router = APIRouter(
    prefix="/meta",
    tags=["Meta"],
)


@router.get("", summary="Capacidades de la instalación")
async def meta() -> MetaRead:
    """Qué ofrece esta instalación, para que un cliente adapte su interfaz antes de
    iniciar sesión (por ejemplo, ocultar "¿Olvidaste tu contraseña?" sin correo).

    Público: no requiere sesión. Solo contiene configuración, nunca datos de
    usuarios.
    """
    return MetaRead(email_enabled=settings.email_enabled)
