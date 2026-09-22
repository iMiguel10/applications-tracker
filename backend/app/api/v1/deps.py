from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.application_service import ApplicationService


# Fábricas de services: una instancia por petición, con la sesión de esa petición.
# Los endpoints dependen de estas funciones, nunca de repositories ni de la sesión.
def get_application_service(
    db: AsyncSession = Depends(get_db),
) -> ApplicationService:
    return ApplicationService(db)
