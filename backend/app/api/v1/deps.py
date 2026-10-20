from fastapi import Depends, Request, Security
from fastapi.security import APIKeyCookie, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python.recipe.emailverification import EmailVerificationClaim
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from app.core.client_ip import client_ip, parse_trusted_proxies
from app.core.config import settings
from app.core.exceptions import AppException, RateLimitedError
from app.db.session import get_db
from app.domain.ai import AiProvider
from app.domain.rate_limits import (
    AI_PER_USER_DAY,
    AI_PER_USER_MINUTE,
    API_PER_USER,
    GENERATE_PER_USER,
    PASSWORD_CHANGE_PER_USER,
    UNSUBSCRIBE_PER_IP,
    UPLOAD_PER_USER,
    RateRule,
)
from app.infra.llm import LLMProvider, build_llm_providers
from app.infra.queue import JobQueue
from app.infra.rate_limit import RateLimiter
from app.infra.storage import FileStorage, LocalFileStorage
from app.schemas.user import CurrentUser
from app.services.account_service import AccountService
from app.services.ai_consent_service import AiConsentService
from app.services.ai_key_service import AiKeyService
from app.services.ai_proposal_service import AiProposalService
from app.services.application_service import ApplicationService
from app.services.application_status_service import ApplicationStatusService
from app.services.calendar_service import CalendarService
from app.services.company_service import CompanyService
from app.services.cv_generation_service import CvGenerationService
from app.services.dashboard_service import DashboardService
from app.services.document_service import DocumentService
from app.services.interview_service import InterviewService
from app.services.limit_service import LimitService
from app.services.password_service import PasswordService
from app.services.profile_entry_service import ProfileEntryService
from app.services.profile_service import ProfileService
from app.services.profile_skill_service import ProfileSkillService
from app.services.reminder_service import ReminderService
from app.services.unsubscribe_service import UnsubscribeService
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


def get_calendar_service(
    db: AsyncSession = Depends(get_db),
) -> CalendarService:
    return CalendarService(db)


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


def get_document_service(
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
) -> DocumentService:
    return DocumentService(db, storage)


def get_ai_proposal_service(
    db: AsyncSession = Depends(get_db),
) -> AiProposalService:
    return AiProposalService(db)


def get_ai_consent_service(
    db: AsyncSession = Depends(get_db),
) -> AiConsentService:
    return AiConsentService(db)


def get_llm_providers() -> dict[AiProvider, LLMProvider]:
    # Los adaptadores no abren conexiones hasta llamar: construirlos no cuesta. La
    # API solo los usa para comprobar una clave al guardarla (RF-153).
    return build_llm_providers(settings)


def get_ai_key_service(
    db: AsyncSession = Depends(get_db),
    providers: dict[AiProvider, LLMProvider] = Depends(get_llm_providers),
) -> AiKeyService:
    return AiKeyService(db, providers=providers)


def get_cv_generation_service(
    db: AsyncSession = Depends(get_db),
) -> CvGenerationService:
    return CvGenerationService(db)


def get_profile_entry_service(
    db: AsyncSession = Depends(get_db),
) -> ProfileEntryService:
    return ProfileEntryService(db)


def get_profile_skill_service(
    db: AsyncSession = Depends(get_db),
) -> ProfileSkillService:
    return ProfileSkillService(db)


def get_profile_service(
    db: AsyncSession = Depends(get_db),
) -> ProfileService:
    return ProfileService(db)


def get_reminder_service(
    db: AsyncSession = Depends(get_db),
) -> ReminderService:
    return ReminderService(db)


def get_unsubscribe_service(
    db: AsyncSession = Depends(get_db),
) -> UnsubscribeService:
    return UnsubscribeService(db)


def get_limit_service(
    db: AsyncSession = Depends(get_db),
) -> LimitService:
    return LimitService(db)


def get_account_service(
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
) -> AccountService:
    return AccountService(db, storage)


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

    Sin correo configurado no se exige (decisión 0013): nadie podría verificar su
    email y la función quedaría bloqueada para siempre en esa instalación.
    """
    if not settings.email_enabled:
        return current_user
    if await session.get_claim_value(EmailVerificationClaim) is True:
        return current_user
    if await users.is_email_verified(current_user.supertokens_user_id):
        await session.fetch_and_set_claim(EmailVerificationClaim)
        return current_user
    raise AppException("Email not verified", status_code=403, code="email_not_verified")


async def enforce_api_rate_limit(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Límite general por usuario de toda la API con sesión (RNF-04; añadido en F11
    a petición del usuario). Va en el router `protected`, después de la sesión:
    sin sesión, el 401 llega antes."""
    limiter: RateLimiter = request.app.state.rate_limiter
    rule = API_PER_USER
    result = await limiter.hit(
        rule.limit, rule.name, rule.key.value, str(current_user.id)
    )
    if not result.allowed:
        raise RateLimitedError(result.retry_after)


async def _enforce_user_rule(
    request: Request, rule: RateRule, current_user: CurrentUser
) -> None:
    limiter: RateLimiter = request.app.state.rate_limiter
    result = await limiter.hit(
        rule.limit, rule.name, rule.key.value, str(current_user.id)
    )
    if not result.allowed:
        raise RateLimitedError(result.retry_after)


async def get_session_handle(
    session: SessionContainer = Depends(_session_dependency),
) -> str:
    """El identificador de la sesión de la petición (cambiar la contraseña cierra
    las demás). Misma instancia de `verify_session()` que get_current_user, así
    que la sesión se valida una sola vez."""
    return session.get_handle()


async def enforce_password_change_rate_limit(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Límite de cambios de contraseña por usuario (issue #2): 5 cada 15 minutos.
    Cuenta todos los intentos, para que no se pueda adivinar la actual."""
    await _enforce_user_rule(request, PASSWORD_CHANGE_PER_USER, current_user)


def get_password_service(request: Request) -> PasswordService:
    return PasswordService(get_job_queue(request), email_enabled=settings.email_enabled)


async def enforce_upload_rate_limit(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Límite de subidas por usuario (ficheros §2, paso 1): cada una lee hasta 5 MB
    y abre el PDF. Se comprueba antes de leer el cuerpo."""
    await _enforce_user_rule(request, UPLOAD_PER_USER, current_user)


async def enforce_generate_rate_limit(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Límite de CVs generados por usuario (F14): cada uno ocupa el `worker`
    maquetando, y el límite de documentos no lo ve si se borran después."""
    await _enforce_user_rule(request, GENERATE_PER_USER, current_user)


async def enforce_ai_rate_limit(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Límite de propuestas de IA por usuario (F15): 5 por minuto y 50 al día.
    Cada una cuesta dinero, de la plataforma o del propio usuario."""
    await _enforce_user_rule(request, AI_PER_USER_MINUTE, current_user)
    await _enforce_user_rule(request, AI_PER_USER_DAY, current_user)


async def enforce_unsubscribe_rate_limit(request: Request) -> None:
    """Límite por IP de la baja de avisos, que responde sin sesión (límites y abuso
    §4). La IP real, detrás de un proxy, sale de TRUSTED_PROXIES."""
    limiter: RateLimiter = request.app.state.rate_limiter
    rule = UNSUBSCRIBE_PER_IP
    ip = client_ip(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
        parse_trusted_proxies(settings.trusted_proxies),
    )
    result = await limiter.hit(rule.limit, rule.name, rule.key.value, ip)
    if not result.allowed:
        raise RateLimitedError(result.retry_after)
