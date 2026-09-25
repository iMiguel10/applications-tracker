from fastapi import Depends, Request, Security
from fastapi.security import APIKeyCookie, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.recipe.emailverification import EmailVerificationClaim
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from app.core.config import settings
from app.core.exceptions import AppException
from app.db.session import get_db
from app.infra.queue import JobQueue
from app.infra.storage import FileStorage, LocalFileStorage
from app.schemas.user import CurrentUser
from app.services.application_service import ApplicationService
from app.services.application_status_service import ApplicationStatusService
from app.services.company_service import CompanyService
from app.services.dashboard_service import DashboardService
from app.services.interview_service import InterviewService
from app.services.limit_service import LimitService
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


# Fábricas de infra: la implementación concreta se elige al arrancar (lifespan de
# main.py) y aquí solo se entrega. En las pruebas se sustituyen con overrides.
def get_job_queue(request: Request) -> JobQueue:
    queue: JobQueue = request.app.state.job_queue
    return queue


def get_file_storage() -> FileStorage:
    # Sin estado: construirlo por petición no cuesta nada.
    return LocalFileStorage(settings.files_root)


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


def get_dashboard_service(
    db: AsyncSession = Depends(get_db),
) -> DashboardService:
    return DashboardService(db)


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


def get_limit_service(
    db: AsyncSession = Depends(get_db),
) -> LimitService:
    return LimitService(db)


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(db)


# Una sola instancia: FastAPI cachea una dependencia por petición solo si es el
# MISMO objeto. Con `verify_session()` escrito en cada sitio, get_current_user y
# require_verified_email validarían la sesión dos veces.
_session_dependency = verify_session()


async def get_current_user(
    session: SessionContainer = Depends(_session_dependency),
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


async def require_verified_email(
    session: SessionContainer = Depends(_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
    users: UserService = Depends(get_user_service),
) -> CurrentUser:
    """Para las funciones con coste (RF-06): 403 `email_not_verified` si el email no
    está verificado. Se declara en lugar de get_current_user y devuelve lo mismo.

    Un "sí" del access token se da por bueno. Un "no" se vuelve a preguntar al core
    antes de rechazar: el claim se calculó al emitir el token, y quien acaba de
    verificar desde otro dispositivo seguiría viendo "no" hasta renovar la sesión
    (autenticación §8, T12). Si el core dice que sí, se actualiza el claim en la
    sesión y las siguientes peticiones ya no preguntan.
    """
    if await session.get_claim_value(EmailVerificationClaim) is True:
        return current_user
    if await users.is_email_verified(current_user.supertokens_user_id):
        await session.fetch_and_set_claim(EmailVerificationClaim)
        return current_user
    raise AppException("Email not verified", status_code=403, code="email_not_verified")
