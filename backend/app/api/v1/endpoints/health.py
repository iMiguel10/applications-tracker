from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health(
    db: AsyncSession = Depends(get_db),
):
    await db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "ok",
        "environment": settings.env,
    }
