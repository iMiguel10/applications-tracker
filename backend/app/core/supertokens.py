from collections.abc import Callable

from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.ingredients.emaildelivery.types import EmailDeliveryConfig
from supertokens_python.recipe import emailpassword, emailverification, session
from supertokens_python.recipe.emailpassword import EmailPasswordOverrideConfig

from app.core.auth_emails import (
    QueuedPasswordResetEmail,
    QueuedVerificationEmail,
    emailpassword_api_overrides,
)
from app.core.config import settings
from app.infra.queue import JobQueue


def init_supertokens(job_queue: Callable[[], JobQueue] | None = None) -> None:
    """Inicializa el SDK. Debe llamarse antes de crear la app de FastAPI.

    Ver docs/arquitectura/autenticacion.md: sesiones por cookies httpOnly y
    receta email + contraseña. El core solo es accesible por la red interna.

    `job_queue` devuelve la cola donde se encolan los emails de SuperTokens. Es una
    función porque la cola se crea después, en el `lifespan` de la API. El
    `worker` no la pasa: inicializa el SDK solo para consultar al core.
    """
    init(
        app_info=InputAppInfo(
            app_name="Applications Tracker",
            api_domain=settings.api_domain,
            # Los enlaces de los emails salen de aquí, no de la petición: en
            # producción debe ser el dominio público (autenticación §8).
            website_domain=settings.website_domain,
            api_base_path="/auth",
            # Solo se usa para construir esos enlaces: con "/", van a las rutas
            # /reset-password y /verify-email del frontend, junto a /login.
            website_base_path="/",
        ),
        supertokens_config=SupertokensConfig(
            connection_uri=settings.supertokens_connection_uri,
            api_key=settings.supertokens_api_key,
        ),
        framework="fastapi",
        recipe_list=[
            # Cookies y cabeceras (decisión 0003). El frontend usa cookies httpOnly
            # (modo por defecto de supertokens-web-js) y nunca ve los tokens. Un
            # cliente que envíe `st-auth-mode: header` en el login los recibe en
            # cabeceras y se autentica con `Authorization: Bearer` (integraciones,
            # Swagger).
            session.init(),
            emailpassword.init(
                email_delivery=EmailDeliveryConfig(
                    service=QueuedPasswordResetEmail(job_queue)
                ),
                override=EmailPasswordOverrideConfig(
                    apis=emailpassword_api_overrides(job_queue)
                ),
            ),
            # OPTIONAL (A38): la sesión vale esté o no verificado el email. Qué
            # exige verificación lo decide el backend endpoint por endpoint, con
            # require_verified_email (RF-06).
            emailverification.init(
                mode="OPTIONAL",
                email_delivery=EmailDeliveryConfig(
                    service=QueuedVerificationEmail(job_queue)
                ),
            ),
        ],
        mode="asgi",
        # Sin envío de datos de uso a SuperTokens.
        telemetry=False,
    )
