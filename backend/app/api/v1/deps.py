from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from app.db.session import get_db
from app.schemas.user import CurrentUser
from app.services.application_service import ApplicationService
from app.services.user_service import UserService


# Fábricas de services: una instancia por petición, con la sesión de esa petición.
# Los endpoints dependen de estas funciones, nunca de repositories ni de la sesión.
def get_application_service(
    db: AsyncSession = Depends(get_db),
) -> ApplicationService:
    return ApplicationService(db)


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(db)


async def get_current_user(
    session: SessionContainer = Depends(verify_session()),
    users: UserService = Depends(get_user_service),
) -> CurrentUser:
    """Única puerta de entrada autenticada (invariante 8).

    verify_session() responde 401 sin sesión válida. Después se obtiene o crea el
    usuario propio. En los tests se sustituye esta dependencia entera.
    """
    return await users.get_or_create(session.get_user_id())
