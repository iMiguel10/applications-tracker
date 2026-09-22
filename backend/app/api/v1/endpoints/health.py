from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthRead

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("", summary="Estado de la API")
async def health(
    db: AsyncSession = Depends(get_db),
) -> HealthRead:
    """Comprueba que la API responde y que llega a la base de datos (`SELECT 1`).

    Público: no requiere sesión.
    """
    await db.execute(text("SELECT 1"))
    return HealthRead(status="ok", database="ok", environment=settings.env)
