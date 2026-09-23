from fastapi import Depends, Security
from fastapi.security import APIKeyCookie, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from app.db.session import get_db
from app.schemas.user import CurrentUser
from app.services.application_service import ApplicationService
from app.services.application_status_service import ApplicationStatusService
from app.services.company_service import CompanyService
from app.services.interview_service import InterviewService
from app.services.reminder_service import ReminderService
from app.services.user_service import UserService

# Esquemas de seguridad SOLO para el OpenAPI: hacen que Swagger muestre el botón
# "Authorize" y el candado en las rutas protegidas. auto_error=False porque no
# validan nada: quien valida la sesión es verify_session(), que acepta ambos modos.
bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="Access token obtenido en `POST /auth/signin` (cabecera de "
    "respuesta `st-access-token`). Caduca a los 5 minutos.",
    auto_error=False,
)
cookie_scheme = APIKeyCookie(
    name="sAccessToken",
    scheme_name="CookieAuth",
    description="Cookie httpOnly que usa el navegador tras un login con "
    "`st-auth-mode: cookie`. Swagger no puede fijarla a mano.",
    auto_error=False,
)
SECURITY_SCHEMES = [Security(bearer_scheme), Security(cookie_scheme)]


# Fábricas de services: una instancia por petición, con la sesión de esa petición.
# Los endpoints dependen de estas funciones, nunca de repositories ni de la sesión.
def get_application_service(
    db: AsyncSession = Depends(get_db),
) -> ApplicationService:
    return ApplicationService(db)


def get_application_status_service(
    db: AsyncSession = Depends(get_db),
) -> ApplicationStatusService:
    return ApplicationStatusService(db)


def get_company_service(
    db: AsyncSession = Depends(get_db),
) -> CompanyService:
    return CompanyService(db)


def get_interview_service(
    db: AsyncSession = Depends(get_db),
) -> InterviewService:
    return InterviewService(db)


def get_reminder_service(
    db: AsyncSession = Depends(get_db),
) -> ReminderService:
    return ReminderService(db)


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(db)


async def get_current_user(
    session: SessionContainer = Depends(verify_session()),
    users: UserService = Depends(get_user_service),
    _bearer: None = Security(bearer_scheme),
    _cookie: None = Security(cookie_scheme),
) -> CurrentUser:
    """Única puerta de entrada autenticada (invariante 8).

    verify_session() responde 401 sin sesión válida (cookie o Bearer). Después se
    obtiene o crea el usuario propio. En los tests se sustituye esta dependencia
    entera. _bearer y _cookie solo existen para documentar la seguridad en el OpenAPI.
    """
    return await users.get_or_create(session.get_user_id())
